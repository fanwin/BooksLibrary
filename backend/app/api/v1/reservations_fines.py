"""
预约和罚款管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.models.models import (
    Reservation, Book, User, Fine, BorrowRecord,
    ReservationStatus, FineStatus, FineType, UserRole, UserStatus
)
from app.schemas.schemas import (
    ReservationCreate, ReservationResponse,
    FineResponse, FinePay
)
from app.api.dependencies import get_current_user, require_admin, require_circulation_admin
from app.core.config import settings

router = APIRouter(tags=["预约和罚款管理"])

# ============ 扩展 Schema ============

class DamageFineCreate(BaseModel):
    """损坏赔偿创建"""
    user_id: int
    borrow_id: int
    amount: float
    description: Optional[str] = None

class LossFineCreate(BaseModel):
    """丢失赔偿创建"""
    user_id: int
    borrow_id: int
    amount: float  # 图书定价或协商金额
    description: Optional[str] = None

class FineCreate(BaseModel):
    """通用罚款创建（管理员）"""
    user_id: int
    fine_type: str  # overdue/damage/loss
    amount: float
    borrow_id: Optional[int] = None
    description: Optional[str] = None

# ============ 预约服务 ============

@router.post("/reservations", response_model=ReservationResponse)
async def create_reservation(
    reservation_data: ReservationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """读者预约已被借出的图书"""
    if current_user.status.value != "active":
        raise HTTPException(status_code=400, detail="用户账户已被禁用，无法预约")

    # 非管理员只能为自己预约
    is_admin = current_user.role.value in [UserRole.SUPER_ADMIN.value, UserRole.CIRCULATION_ADMIN.value]
    if not is_admin and reservation_data.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="只能为自己预约")

    # 检查是否已预约该书（含待取书状态）
    existing = db.query(Reservation).filter(
        and_(
            Reservation.user_id == reservation_data.user_id,
            Reservation.book_id == reservation_data.book_id,
            Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.READY])
        )
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="您已预约了该图书，请勿重复预约")

    # 检查预约数量限制
    pending_count = db.query(Reservation).filter(
        and_(
            Reservation.user_id == reservation_data.user_id,
            Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.READY])
        )
    ).count()

    max_reservations = settings.MAX_RESERVATION_COUNT
    if pending_count >= max_reservations:
        raise HTTPException(
            status_code=400,
            detail=f"已达到最大预约数量{max_reservations}本，当前有{pending_count}条有效预约"
        )

    book = db.query(Book).filter(Book.book_id == reservation_data.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")

    if book.available_copies > 0:
        raise HTTPException(
            status_code=400,
            detail=f"《{book.title}》当前有{book.available_copies}本可借，无需预约"
        )

    # 获取排队位置（同一本书多人预约自动排队）
    queue_position = db.query(Reservation).filter(
        and_(
            Reservation.book_id == reservation_data.book_id,
            Reservation.status == ReservationStatus.PENDING
        )
    ).count() + 1

    reservation = Reservation(
        user_id=reservation_data.user_id,
        book_id=reservation_data.book_id,
        queue_position=queue_position,
        status=ReservationStatus.PENDING
    )

    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return reservation


@router.get("/reservations", response_model=dict)
async def list_reservations(
    user_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询预约记录列表（管理员可查看全部）"""
    query = db.query(Reservation)

    is_admin = current_user.role.value in [
        UserRole.SUPER_ADMIN.value, UserRole.CIRCULATION_ADMIN.value
    ]

    # 非管理员只能看自己的预约
    if not is_admin:
        user_id = current_user.user_id

    if user_id:
        query = query.filter(Reservation.user_id == user_id)

    if status_filter:
        try:
            query = query.filter(Reservation.status == ReservationStatus(status_filter))
        except ValueError:
            pass

    total = query.count()
    reservations = query.order_by(Reservation.reservation_date.desc())\
        .offset((page - 1) * size)\
        .limit(size)\
        .all()

    items = []
    for r in reservations:
        user_info = db.query(User).filter(User.user_id == r.user_id).first()
        book_info = db.query(Book).filter(Book.book_id == r.book_id).first()

        items.append({
            "reservation_id": r.reservation_id,
            "user_id": r.user_id,
            "username": user_info.username if user_info else "未知",
            "book_id": r.book_id,
            "title": book_info.title if book_info else "未知图书",
            "author": book_info.author if book_info else "",
            "reservation_date": r.reservation_date.strftime("%Y-%m-%d %H:%M") if r.reservation_date else "",
            "expiry_date": r.expiry_date.strftime("%Y-%m-%d") if r.expiry_date else None,
            "status": r.status.value,
            "status_text": _get_reservation_status_text(r.status.value),
            "queue_position": r.queue_position,
            "notification_sent": r.notification_sent,
            # 计算是否超期未取
            "is_expired": (r.status == ReservationStatus.READY and r.expiry_date and r.expiry_date < datetime.now()),
            "days_until_expiry": max(0, (r.expiry_date - datetime.now()).days) if r.expiry_date and r.expiry_date > datetime.now() else None
        })

    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    }


@router.post("/reservations/{reservation_id}/cancel")
async def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消预约（读者主动取消）"""
    reservation = db.query(Reservation).filter(
        Reservation.reservation_id == reservation_id
    ).first()

    if not reservation:
        raise HTTPException(status_code=404, detail="预约记录不存在")

    # 权限：只能取消自己的预约，管理员可取消任何
    if current_user.role.value not in [UserRole.SUPER_ADMIN.value, UserRole.CIRCULATION_ADMIN.value]:
        if reservation.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="无权取消他人预约")

    if reservation.status not in [ReservationStatus.PENDING, ReservationStatus.READY]:
        raise HTTPException(status_code=400, detail=f"该预约状态为'{reservation.status.value}'，不可取消")

    old_status = reservation.status.value
    old_position = reservation.queue_position
    reservation.status = ReservationStatus.CANCELLED

    # 更新后续排队者的位置（前移一位）
    db.query(Reservation).filter(
        and_(
            Reservation.book_id == reservation.book_id,
            Reservation.status == ReservationStatus.PENDING,
            Reservation.queue_position > old_position
        )
    ).update({Reservation.queue_position: Reservation.queue_position - 1})

    db.commit()

    return {
        "code": 200,
        "message": "预约已成功取消",
        "data": {
            "reservation_id": reservation_id,
            "previous_status": old_status,
            "queue_position_released": True
        }
    }


@router.post("/reservations/{reservation_id}/pickup")
async def pickup_reserved_book(
    reservation_id: int,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """馆员操作：预约图书取书确认"""
    reservation = db.query(Reservation).filter(
        Reservation.reservation_id == reservation_id
    ).first()

    if not reservation:
        raise HTTPException(status_code=404, detail="预约记录不存在")

    if reservation.status != ReservationStatus.READY:
        raise HTTPException(status_code=400, detail="该预约尚未到可取书状态")

    # 标记为已履约
    reservation.status = ReservationStatus.FULFILLED
    reservation.notification_sent = True

    db.commit()

    return {
        "code": 200,
        "message": "取书确认成功，预约已完成",
        "data": {"reservation_id": reservation_id}
    }


@router.post("/reservations/check-expired")
async def check_and_release_expired_reservations(
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """检查并释放超期未取的预约（定时任务/手动触发）"""
    now = datetime.now()
    expired_reservations = db.query(Reservation).filter(
        and_(
            Reservation.status == ReservationStatus.READY,
            Reservation.expiry_date < now
        )
    ).all()

    released_count = 0
    for res in expired_reservations:
        old_pos = res.queue_position
        res.status = ReservationStatus.EXPIRED

        # 后续排队者位置前移
        db.query(Reservation).filter(
            and_(
                Reservation.book_id == res.book_id,
                Reservation.status == ReservationStatus.PENDING,
                Reservation.queue_position > old_pos
            )
        ).update({Reservation.queue_position: Reservation.queue_position - 1})

        released_count += 1

        # 检查是否有下一位等待者，将其设为READY
        next_reservation = db.query(Reservation).filter(
            and_(
                Reservation.book_id == res.book_id,
                Reservation.status == ReservationStatus.PENDING
            )
        ).order_by(Reservation.queue_position.asc()).first()

        if next_reservation:
            next_reservation.status = ReservationStatus.READY
            next_reservation.expiry_date = now + timedelta(days=settings.RESERVATION_HOLD_DAYS)
            next_reservation.notification_sent = False  # 触发通知

    db.commit()

    return {
        "code": 200,
        "message": f"检查完成，释放{released_count}条超期预约",
        "data": {
            "released_count": released_count,
            "check_time": now.isoformat()
        }
    }


@router.get("/reservations/book/{book_id}/queue")
async def get_book_reservation_queue(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查看某本书的预约排队情况"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")

    queue = db.query(Reservation).filter(
        and_(
            Reservation.book_id == book_id,
            Reservation.status == ReservationStatus.PENDING
        )
    ).order_by(Reservation.queue_position.asc()).all()

    items = []
    for q in queue:
        user_info = db.query(User).filter(User.user_id == q.user_id).first()
        items.append({
            "position": q.queue_position,
            "user_id": q.user_id,
            "username": user_info.username if user_info else "未知",
            "reservation_date": q.reservation_date.strftime("%Y-%m-%d") if q.reservation_date else ""
        })

    return {
        "code": 200,
        "data": {
            "book_id": book_id,
            "title": book.title,
            "available_copies": book.available_copies,
            "total_copies": book.total_copies,
            "queue_length": len(items),
            "queue": items
        }
    }

# ============ 罚款管理 ============

@router.get("/fines", response_model=dict)
async def list_fines(
    user_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    fine_type_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询罚款记录列表"""
    query = db.query(Fine)

    is_admin_or_circulation = current_user.role.value in [
        UserRole.SUPER_ADMIN.value, UserRole.CIRCULATION_ADMIN.value
    ]

    if not is_admin_or_circulation:
        if user_id and user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="无权查看他人罚款")
        user_id = current_user.user_id
    elif user_id:
        query = query.filter(Fine.user_id == user_id)

    if status_filter:
        try:
            query = query.filter(Fine.status == FineStatus(status_filter))
        except ValueError:
            pass

    if fine_type_filter:
        try:
            query = query.filter(Fine.fine_type == FineType(fine_type_filter))
        except ValueError:
            pass

    total = query.count()
    fines = query.order_by(Fine.created_at.desc())\
        .offset((page - 1) * size)\
        .limit(size)\
        .all()

    items = []
    for f in fines:
        user_info = db.query(User).filter(User.user_id == f.user_id).first()
        borrow_info = None
        book_title = ""

        if f.borrow_id:
            borrow_info = db.query(BorrowRecord).filter(BorrowRecord.borrow_id == f.borrow_id).first()
            if borrow_info:
                from app.models.models import BookCopy
                copy_info = db.query(BookCopy).filter(BookCopy.copy_id == borrow_info.copy_id).first()
                if copy_info:
                    book = db.query(Book).filter(Book.book_id == copy_info.book_id).first()
                    book_title = book.title if book else ""

        items.append({
            "fine_id": f.fine_id,
            "user_id": f.user_id,
            "username": user_info.username if user_info else "未知",
            "borrow_id": f.borrow_id,
            "book_title": book_title or ("--" if f.fine_type != FineType.LOSS else ""),
            "fine_type": f.fine_type.value,
            "fine_type_text": _get_fine_type_text(f.fine_type.value),
            "amount": round(f.amount, 2),
            "status": f.status.value,
            "status_text": _get_fine_status_text(f.status.value),
            "paid_date": f.paid_date.strftime("%Y-%m-%d") if f.paid_date else None,
            "created_at": f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else ""
        })

    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    }


@router.post("/fines/{fine_id}/pay")
async def pay_fine(
    fine_id: int,
    pay_data: FinePay,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """缴纳罚款（支持模拟在线支付和线下缴纳）"""
    fine = db.query(Fine).filter(Fine.fine_id == fine_id).first()
    if not fine:
        raise HTTPException(status_code=404, detail="罚款记录不存在")

    if fine.status == FineStatus.PAID:
        raise HTTPException(status_code=400, detail="该罚款已于{}缴纳".format(
            fine.paid_date.strftime("%Y-%m-%d") if fine.paid_date else "未知时间"
        ))

    if abs(pay_data.amount - fine.amount) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"支付金额不匹配：应缴￥{fine.amount:.2f}，收到￥{pay_data.amount:.2f}"
        )

    fine.status = FineStatus.PAID
    fine.paid_date = datetime.now()

    # 检查用户是否应该解冻借阅权限
    user = db.query(User).filter(User.user_id == fine.user_id).first()
    auto_unfreeze = False
    if user:
        remaining_pending = db.query(Fine).filter(
            and_(
                Fine.user_id == fine.user_id,
                Fine.status == FineStatus.PENDING
            )
        ).count()

        # 缴清所有罚款后自动解冻（如果因罚款被冻结）
        if remaining_pending == 0 and user.status.value == "suspended":
            user.status = UserStatus.ACTIVE
            auto_unfreeze = True

    db.commit()

    return {
        "code": 200,
        "message": "罚款缴纳成功" + ("，借阅权限已自动恢复" if auto_unfreeze else ""),
        "data": {
            "fine_id": fine_id,
            "paid_amount": round(pay_data.amount, 2),
            "paid_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "payment_method": pay_data.__dict__.get("method", "unknown"),
            "auto_unfreeze": auto_unfreeze
        }
    }


@router.post("/fines/damage")
async def create_damage_fine(
    fine_data: DamageFineCreate,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """创建图书损坏赔偿罚款"""
    user = db.query(User).filter(User.user_id == fine_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    borrow = db.query(BorrowRecord).filter(BorrowRecord.borrow_id == fine_data.borrow_id).first()
    if not borrow:
        raise HTTPException(status_code=404, detail="借阅记录不存在")

    fine = Fine(
        user_id=fine_data.user_id,
        borrow_id=fine_data.borrow_id,
        fine_type=FineType.DAMAGE,
        amount=fine_data.amount,
        status=FineStatus.PENDING
    )

    db.add(fine)
    db.commit()
    db.refresh(fine)

    # 检查是否需要自动冻结
    _check_and_freeze_user(db, fine_data.user_id)

    return {
        "code": 200,
        "message": "损坏赔偿罚款已创建",
        "data": {
            "fine_id": fine.fine_id,
            "amount": fine.amount,
            "type": "damage"
        }
    }


@router.post("/fines/loss")
async def create_loss_fine(
    fine_data: LossFineCreate,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """创建图书丢失赔偿罚款"""
    user = db.query(User).filter(User.user_id == fine_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    borrow = db.query(BorrowRecord).filter(BorrowRecord.borrow_id == fine_data.borrow_id).first()
    if not borrow:
        raise HTTPException(status_code=404, detail="借阅记录不存在")

    # 更新借阅记录状态为丢失
    borrow.status = BorrowStatus.LOST

    # 更新副本状态
    from app.models.models import BookCopy
    copy = db.query(BookCopy).filter(BookCopy.copy_id == borrow.copy_id).first()
    if copy:
        copy.status = BookCopy.LOST if hasattr(BookCopy, 'LOST') else "lost"

    fine = Fine(
        user_id=fine_data.user_id,
        borrow_id=fine_data.borrow_id,
        fine_type=FineType.LOSS,
        amount=fine_data.amount,
        status=FineStatus.PENDING
    )

    db.add(fine)
    db.commit()
    db.refresh(fine)

    # 检查是否需要自动冻结
    _check_and_freeze_user(db, fine_data.user_id)

    return {
        "code": 200,
        "message": "丢失赔偿罚款已创建，借阅记录已标记为丢失",
        "data": {
            "fine_id": fine.fine_id,
            "amount": fine.amount,
            "type": "loss"
        }
    }


@router.post("/fines/{fine_id}/waive")
async def waive_fine(
    fine_id: int,
    reason: str = "",
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """管理员免除罚款"""
    fine = db.query(Fine).filter(Fine.fine_id == fine_id).first()
    if not fine:
        raise HTTPException(status_code=404, detail="罚款记录不存在")

    if fine.status == FineStatus.PAID:
        raise HTTPException(status_code=400, detail="该罚款已缴纳，无法免除")

    if fine.status == FineStatus.WAIVED:
        raise HTTPException(status_code=400, detail="该罚款已被免除")

    old_status = fine.status.value
    fine.status = FineStatus.WAIVED

    db.commit()

    return {
        "code": 200,
        "message": "罚款已免除",
        "data": {
            "fine_id": fine_id,
            "previous_status": old_status,
            "reason": reason or "管理员操作"
        }
    }


@router.get("/users/{user_id}/fines/summary")
async def get_user_fines_summary(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户罚款汇总（用于判断是否可借阅）"""
    if current_user.role.value != UserRole.SUPER_ADMIN.value and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权查看他人罚款汇总")

    pending_fines = db.query(Fine).filter(
        and_(
            Fine.user_id == user_id,
            Fine.status == FineStatus.PENDING
        )
    ).all()

    total_pending = sum(f.amount for f in pending_fines)
    total_paid = db.query(Fine).filter(
        and_(
            Fine.user_id == user_id,
            Fine.status == FineStatus.PAID
        )
    ).with_entities(func.sum(Fine.amount)).scalar() or 0

    # 判断是否被冻结（阈值从SystemConfig读取，默认50元）
    from app.models.models import SystemConfig
    threshold_config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "fine_freeze_threshold"
    ).first()
    frozen_threshold = float(threshold_config.config_value) if threshold_config and threshold_config.config_value else 50
    is_frozen = total_pending >= frozen_threshold
    can_borrow = len(pending_fines) == 0

    # 按类型统计
    overdue_total = sum(f.amount for f in pending_fines if f.fine_type == FineType.OVERDUE)
    damage_total = sum(f.amount for f in pending_fines if f.fine_type == FineType.DAMAGE)
    loss_total = sum(f.amount for f in pending_fines if f.fine_type == FineType.LOSS)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "pending_count": len(pending_fines),
            "pending_amount": round(total_pending, 2),
            "paid_amount": round(total_paid, 2),
            "can_borrow": can_borrow,
            "is_frozen": is_frozen,
            "frozen_threshold": frozen_threshold,
            "breakdown": {
                "overdue": round(overdue_total, 2),
                "damage": round(damage_total, 2),
                "loss": round(loss_total, 2)
            }
        }
    }


# ============ 辅助函数 ============

def _check_and_freeze_user(db: Session, user_id: int) -> bool:
    """检查用户累计罚款是否超过冻结阈值，超限则自动冻结"""
    from app.models.models import SystemConfig, UserStatus
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or user.status != UserStatus.ACTIVE:
        return False

    total_pending = db.query(Fine).filter(
        and_(Fine.user_id == user_id, Fine.status == FineStatus.PENDING)
    ).with_entities(func.sum(Fine.amount)).scalar() or 0

    threshold_config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "fine_freeze_threshold"
    ).first()
    freeze_threshold = float(threshold_config.config_value) if threshold_config and threshold_config.config_value else 50

    if total_pending >= freeze_threshold:
        user.status = UserStatus.SUSPENDED
        db.commit()
        return True
    return False

def _get_reservation_status_text(status: str) -> str:
    """预约状态中文映射"""
    mapping = {
        "pending": "排队中",
        "ready": "可取书",
        "fulfilled": "已完成",
        "cancelled": "已取消",
        "expired": "已过期（超时未取）"
    }
    return mapping.get(status, status)


def _get_fine_type_text(fine_type: str) -> str:
    """罚款类型中文映射"""
    mapping = {
        "overdue": "逾期罚款",
        "damage": "损坏赔偿",
        "loss": "丢失赔偿"
    }
    return mapping.get(fine_type, fine_type)


def _get_fine_status_text(status: str) -> str:
    """罚款状态中文映射"""
    mapping = {
        "pending": "待缴纳",
        "paid": "已缴纳",
        "waived": "已免除"
    }
    return mapping.get(status, status)
