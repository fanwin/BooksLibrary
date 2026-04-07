"""
借阅管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.models.models import (
    BorrowRecord, Book, BookCopy, User,
    BorrowStatus, CopyStatus, BookStatus, UserRole, UserStatus, Notification
)
from app.schemas.schemas import BorrowCreate, BorrowResponse, BorrowReturn, BorrowRenew
from app.api.dependencies import get_current_user, require_admin, require_circulation_admin
from app.core.config import settings

router = APIRouter(prefix="/borrows", tags=["借阅管理"])

# ============ 扩展 Schema ============

class BatchBorrowCreate(BaseModel):
    """批量借阅"""
    user_id: int
    copy_ids: List[int]

class BatchBorrowResponse(BaseModel):
    """批量借阅响应"""
    success_count: int
    fail_count: int
    success_items: list
    fail_items: list

class BorrowListResponse(BaseModel):
    """借阅列表响应"""
    items: list
    total: int
    page: int
    size: int

# ============ 核心函数 ============

def calculate_due_date(borrow_days: int = None, db: Session = None) -> datetime:
    """计算应还日期（考虑节假日顺延，跳过周末和法定节假日）"""
    days = borrow_days or settings.DEFAULT_BORROW_DAYS
    due_date = datetime.now()

    # 尝试查询Holiday表实现节假日顺延
    holidays_set = set()
    if db:
        try:
            from app.models.models import Holiday
            current_year = due_date.year
            holidays = db.query(Holiday).filter(Holiday.year == current_year).all()
            for h in holidays:
                if h.date:
                    # 只取日期部分用于比较
                    holidays_set.add(h.date.date() if hasattr(h.date, 'date') else h.date)
        except Exception:
            pass  # Holiday表不存在时降级为简单计算

    # 累加工作日（跳过周末和法定节假日）
    added = 0
    while added < days:
        due_date += timedelta(days=1)
        # 跳过周六(5)和周日(6)
        if due_date.weekday() >= 5:
            continue
        # 跳过法定节假日
        due_date_date = due_date.date() if hasattr(due_date, 'date') else due_date
        if due_date_date in holidays_set:
            continue
        added += 1

    return due_date

def check_borrow_eligibility(user: User, db: Session) -> dict:
    """检查用户借阅资格"""
    if user.status.value != "active":
        return {"eligible": False, "reason": "用户账户已被禁用或冻结"}

    active_borrows = db.query(BorrowRecord).filter(
        and_(
            BorrowRecord.user_id == user.user_id,
            BorrowRecord.status == BorrowStatus.ACTIVE
        )
    ).count()

    max_borrow = user.max_borrow_count or settings.MAX_BORROW_COUNT
    if active_borrows >= max_borrow:
        return {"eligible": False, "reason": f"已达到最大借阅数量{max_borrow}本，当前已借{active_borrows}本"}

    overdue_borrows = db.query(BorrowRecord).filter(
        and_(
            BorrowRecord.user_id == user.user_id,
            BorrowRecord.status == BorrowStatus.ACTIVE,
            BorrowRecord.due_date < datetime.now()
        )
    ).count()

    if overdue_borrows > 0:
        return {"eligible": False, "reason": f"有{overdue_borrows}本图书逾期未还，请先归还后再借阅"}

    from app.models.models import Fine, FineStatus, SystemConfig
    total_unpaid = db.query(Fine).filter(
        and_(
            Fine.user_id == user.user_id,
            Fine.status == FineStatus.PENDING
        )
    ).with_entities(func.sum(Fine.amount)).scalar() or 0

    # 从SystemConfig读取冻结阈值，默认50元
    threshold_config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "fine_freeze_threshold"
    ).first()
    freeze_threshold = float(threshold_config.config_value) if threshold_config and threshold_config.config_value else 50

    if total_unpaid >= freeze_threshold:
        return {"eligible": False, "reason": f"累计未缴罚款￥{total_unpaid:.2f}已达冻结阈值￥{freeze_threshold:.2f}，请缴纳后再借阅"}

    return {"eligible": True}

# ============ 借书接口 ============

@router.post("", response_model=BorrowResponse)
async def borrow_book(
    borrow_data: BorrowCreate,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """单本借书"""
    reader = db.query(User).filter(User.user_id == borrow_data.user_id).first()
    if not reader:
        raise HTTPException(status_code=404, detail="读者不存在")

    eligibility = check_borrow_eligibility(reader, db)
    if not eligibility["eligible"]:
        raise HTTPException(status_code=400, detail=eligibility["reason"])

    copy = db.query(BookCopy).filter(BookCopy.copy_id == borrow_data.copy_id).first()
    if not copy:
        raise HTTPException(status_code=404, detail="图书副本不存在")

    if copy.status != CopyStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="该图书副本当前不可借阅（状态：{}）".format(copy.status.value))

    # 检查是否有有效预约且不是该读者自己的
    from app.models.models import Reservation, ReservationStatus
    existing_reservations = db.query(Reservation).filter(
        and_(
            Reservation.book_id == copy.book_id,
            Reservation.status == ReservationStatus.PENDING,
            Reservation.user_id != borrow_data.user_id
        )
    ).first()

    if existing_reservations:
        book = db.query(Book).filter(Book.book_id == copy.book_id).first()
        raise HTTPException(
            status_code=400,
            detail=f"《{book.title}》已被其他读者预约，不可借阅"
        )

    # 如果该书有READY状态的预约是给当前读者的，标记为已履约
    my_ready_reservation = db.query(Reservation).filter(
        and_(
            Reservation.book_id == copy.book_id,
            Reservation.status == ReservationStatus.READY,
            Reservation.user_id == borrow_data.user_id
        )
    ).first()
    if my_ready_reservation:
        my_ready_reservation.status = ReservationStatus.FULFILLED

    due_date = calculate_due_date(reader.borrow_limit_days, db=db)

    borrow_record = BorrowRecord(
        user_id=borrow_data.user_id,
        copy_id=borrow_data.copy_id,
        due_date=due_date,
        status=BorrowStatus.ACTIVE,
        operator_id=current_user.user_id
    )

    copy.status = CopyStatus.BORROWED

    book = db.query(Book).filter(Book.book_id == copy.book_id).first()
    book.available_copies = max(0, (book.available_copies or 1) - 1)
    if book.available_copies <= 0:
        book.status = BookStatus.BORROWED

    db.add(borrow_record)
    db.commit()
    db.refresh(borrow_record)

    return borrow_record


@router.post("/batch", response_model=BatchBorrowResponse)
async def batch_borrow_books(
    batch_data: BatchBorrowCreate,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """批量借阅：一次扫描多本图书完成借阅"""
    reader = db.query(User).filter(User.user_id == batch_data.user_id).first()
    if not reader:
        raise HTTPException(status_code=404, detail="读者不存在")

    eligibility = check_borrow_eligibility(reader, db)
    if not eligibility["eligible"]:
        raise HTTPException(status_code=400, detail=eligibility["reason"])

    success_items = []
    fail_items = []

    for copy_id in batch_data.copy_ids:
        try:
            copy = db.query(BookCopy).filter(BookCopy.copy_id == copy_id).first()
            if not copy:
                fail_items.append({"copy_id": copy_id, "reason": "图书副本不存在"})
                continue

            if copy.status != CopyStatus.AVAILABLE:
                fail_items.append({"copy_id": copy_id, "reason": f"副本不可借（{copy.status.value}）"})
                continue

            due_date = calculate_due_date(reader.borrow_limit_days, db=db)

            borrow_record = BorrowRecord(
                user_id=batch_data.user_id,
                copy_id=copy_id,
                due_date=due_date,
                status=BorrowStatus.ACTIVE,
                operator_id=current_user.user_id
            )

            copy.status = CopyStatus.BORROWED

            book = db.query(Book).filter(Book.book_id == copy.book_id).first()
            book.available_copies = max(0, (book.available_copies or 1) - 1)
            if book.available_copies <= 0:
                book.status = BookStatus.BORROWED

            db.add(borrow_record)
            db.flush()

            success_items.append({
                "copy_id": copy_id,
                "borrow_id": borrow_record.borrow_id,
                "due_date": due_date.strftime("%Y-%m-%d %H:%M")
            })

            # 重新检查借阅上限
            current_count = db.query(BorrowRecord).filter(
                and_(
                    BorrowRecord.user_id == batch_data.user_id,
                    BorrowRecord.status == BorrowStatus.ACTIVE
                )
            ).count()

            if current_count >= (reader.max_borrow_count or settings.MAX_BORROW_COUNT):
                remaining = [cid for cid in batch_data.copy_ids if cid > copy_id]
                for r_id in remaining:
                    fail_items.append({"copy_id": r_id, "reason": "已达到最大借阅数量"})
                break

        except Exception as e:
            db.rollback()
            fail_items.append({"copy_id": copy_id, "reason": str(e)})
            continue

    db.commit()

    return {
        "success_count": len(success_items),
        "fail_count": len(fail_items),
        "success_items": success_items,
        "fail_items": fail_items
    }

# ============ 还书接口 ============

@router.post("/{borrow_id}/return")
async def return_book(
    borrow_id: int,
    return_data: Optional[BorrowReturn] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """还书（支持异地还书）"""
    borrow = db.query(BorrowRecord).filter(BorrowRecord.borrow_id == borrow_id).first()
    if not borrow:
        raise HTTPException(status_code=404, detail="借阅记录不存在")

    # 权限：普通用户只能还自己的书
    if current_user.role.value not in [UserRole.SUPER_ADMIN.value, UserRole.CIRCULATION_ADMIN.value]:
        if borrow.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="只能归还自己的借阅")

    if borrow.status == BorrowStatus.RETURNED:
        raise HTTPException(status_code=400, detail="该图书已归还")

    # 计算逾期信息
    now = datetime.now()
    fine_amount = 0
    overdue_days = 0
    grace_days = settings.FINE_GRACE_DAYS
    auto_frozen = False

    if borrow.due_date < now:
        overdue_days = (now - borrow.due_date).days
        if overdue_days > grace_days:
            fine_days = overdue_days - grace_days
            fine_amount = fine_days * settings.DAILY_FINE_AMOUNT

    # 更新借阅记录
    borrow.return_date = now
    borrow.status = BorrowStatus.RETURNED
    borrow.fine_amount = fine_amount
    # 支持异地还书：记录归还分馆
    if return_data and return_data.return_branch:
        borrow.return_branch = return_data.return_branch

    # 更新副本状态
    copy = db.query(BookCopy).filter(BookCopy.copy_id == borrow.copy_id).first()
    if copy:
        # 先检查是否有预约排队（在改副本状态之前判断）
        from app.models.models import Reservation, ReservationStatus
        reservation = db.query(Reservation).filter(
            and_(
                Reservation.book_id == copy.book_id,
                Reservation.status == ReservationStatus.PENDING
            )
        ).order_by(Reservation.reservation_date.asc()).first()

        if reservation:
            # 有预约 → 副本直接变为预留状态
            copy.status = CopyStatus.RESERVED

            book = db.query(Book).filter(Book.book_id == copy.book_id).first()
            if book:
                book.status = BookStatus.RESERVED
            reservation.status = ReservationStatus.READY
            reservation.expiry_date = now + timedelta(days=settings.RESERVATION_HOLD_DAYS)
            reservation.notification_sent = True

            db.add(Notification(
                user_id=reservation.user_id,
                title="预约图书已到，请及时取书",
                content=f"您预约的《{book.title}》已有副本归还并为您预留。"
                        f"请在 {reservation.expiry_date.strftime('%Y-%m-%d')} 前到馆取书。",
                type="reservation_ready",
            ))
        else:
            # 无预约 → 副本恢复可借，增加可借数
            copy.status = CopyStatus.AVAILABLE

            book = db.query(Book).filter(Book.book_id == copy.book_id).first()
            if book:
                book.available_copies = (book.available_copies or 0) + 1
                if book.available_copies > 0 and book.status == BookStatus.BORROWED:
                    book.status = BookStatus.AVAILABLE

    # 创建罚款记录
    if fine_amount > 0:
        from app.models.models import Fine, FineType, FineStatus, SystemConfig
        fine = Fine(
            user_id=borrow.user_id,
            borrow_id=borrow.borrow_id,
            fine_type=FineType.OVERDUE,
            amount=fine_amount,
            status=FineStatus.PENDING
        )
        db.add(fine)

        # 检查是否需要自动冻结（累计罚款超过阈值）
        reader = db.query(User).filter(User.user_id == borrow.user_id).first()
        if reader and reader.status == UserStatus.ACTIVE:
            total_pending_fines = db.query(Fine).filter(
                and_(
                    Fine.user_id == borrow.user_id,
                    Fine.status == FineStatus.PENDING
                )
            ).with_entities(func.sum(Fine.amount)).scalar() or 0
            threshold_config = db.query(SystemConfig).filter(
                SystemConfig.config_key == "fine_freeze_threshold"
            ).first()
            freeze_threshold = float(threshold_config.config_value) if threshold_config and threshold_config.config_value else 50
            if total_pending_fines >= freeze_threshold:
                reader.status = UserStatus.SUSPENDED
                auto_frozen = True

    db.commit()

    return {
        "code": 200,
        "message": "还书成功" + ("，借阅权限已自动冻结" if auto_frozen else ""),
        "data": {
            "borrow_id": borrow.borrow_id,
            "return_date": now.strftime("%Y-%m-%d %H:%M:%S"),
            "fine_amount": round(fine_amount, 2),
            "overdue_days": max(0, overdue_days - grace_days) if overdue_days > grace_days else 0,
            "has_reservation": bool(reservation if 'reservation' in dir() else None),
            "auto_frozen": auto_frozen,
            "return_branch": borrow.return_branch
        }
    }

# ============ 续借接口 ============

@router.post("/{borrow_id}/renew")
async def renew_book(
    borrow_id: int,
    renew_data: Optional[BorrowRenew] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """在线续借申请"""
    borrow = db.query(BorrowRecord).filter(BorrowRecord.borrow_id == borrow_id).first()
    if not borrow:
        raise HTTPException(status_code=404, detail="借阅记录不存在")

    # 权限检查
    if current_user.role.value not in [UserRole.SUPER_ADMIN.value, UserRole.CIRCULATION_ADMIN.value]:
        if borrow.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="只能续借自己的图书")

    if borrow.status != BorrowStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="该借阅记录状态不可续借（当前状态：{}）".format(borrow.status.value))

    # 检查续借条件
    max_renew = settings.MAX_RENEW_COUNT
    if borrow.renew_count >= max_renew:
        raise HTTPException(
            status_code=400,
            detail=f"已达到最大续借次数{max_renew}次（已续借{borrow.renew_count}次）"
        )

    if borrow.due_date < datetime.now():
        overdue_days = (datetime.now() - borrow.due_date).days
        raise HTTPException(
            status_code=400,
            detail=f"图书已超期{overdue_days}天，不可续借，请先归还并缴纳罚款"
        )

    # 检查是否被预约
    copy = db.query(BookCopy).filter(BookCopy.copy_id == borrow.copy_id).first()
    if copy:
        book = db.query(Book).filter(Book.book_id == copy.book_id).first()
        if book:
            from app.models.models import Reservation, ReservationStatus
            has_reservation = db.query(Reservation).filter(
                and_(
                    Reservation.book_id == book.book_id,
                    Reservation.status == ReservationStatus.PENDING,
                    Reservation.user_id != borrow.user_id
                )
            ).first()

            if has_reservation:
                raise HTTPException(
                    status_code=400,
                    detail="该图书已被其他读者预约，不可续借"
                )

    # 执行续借
    old_due_date = borrow.due_date
    renew_period = settings.RENEW_DAYS
    # 使用节假日顺延计算新应还日期
    new_due_date = calculate_due_date(renew_period, db=db)
    # 从旧到期日之后开始计算
    borrow.due_date = new_due_date
    borrow.renew_count += 1

    db.commit()

    return {
        "code": 200,
        "message": "续借成功",
        "data": {
            "borrow_id": borrow.borrow_id,
            "old_due_date": old_due_date.strftime("%Y-%m-%d"),
            "new_due_date": borrow.due_date.strftime("%Y-%m-%d"),
            "renew_count": borrow.renew_count,
            "max_renew_count": max_renew,
            "renew_days": renew_period
        }
    }

# ============ 借书辅助接口 ============

@router.get("/check-eligibility/{user_id}", response_model=dict)
async def check_eligibility(
    user_id: int,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """检查读者借阅资格"""
    reader = db.query(User).filter(User.user_id == user_id).first()
    if not reader:
        raise HTTPException(status_code=404, detail="读者不存在")

    result = check_borrow_eligibility(reader, db)
    result["reader"] = {
        "user_id": reader.user_id,
        "username": reader.username,
        "reader_card_number": reader.reader_card_number,
        "reader_type": reader.reader_type,
        "status": reader.status.value,
        "max_borrow_count": reader.max_borrow_count,
        "borrow_limit_days": reader.borrow_limit_days,
    }
    return {"code": 200, "data": result}


@router.get("/lookup-copy", response_model=dict)
async def lookup_copy_by_barcode(
    barcode: str = Query(..., description="图书条码"),
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """根据条码查询副本信息（借书时扫码用）"""
    copy = db.query(BookCopy).filter(BookCopy.barcode == barcode).first()
    if not copy:
        raise HTTPException(status_code=404, detail="未找到该条码对应的图书副本")

    book = db.query(Book).filter(Book.book_id == copy.book_id).first()
    return {
        "code": 200,
        "data": {
            "copy_id": copy.copy_id,
            "barcode": copy.barcode,
            "status": copy.status.value,
            "location_detail": copy.location_detail,
            "book_id": book.book_id if book else None,
            "title": book.title if book else "未知",
            "author": book.author if book else "",
            "isbn": book.isbn if book else "",
        }
    }


# ============ 查询接口 ============

@router.get("", response_model=dict)
async def list_borrows(
    user_id: Optional[int] = Query(None, description="按用户ID筛选"),
    status_filter: Optional[str] = Query(None, description="按状态筛选：active/returned/overdue"),
    keyword: Optional[str] = Query(None, description="关键词搜索（书名/读者名）"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询借阅记录列表（管理员可查看所有）"""
    query = db.query(BorrowRecord)

    # 权限控制
    is_admin = current_user.role.value in [
        UserRole.SUPER_ADMIN.value, UserRole.CIRCULATION_ADMIN.value
    ]
    if not is_admin:
        user_id = current_user.user_id

    if user_id:
        query = query.filter(BorrowRecord.user_id == user_id)
    if status_filter:
        try:
            query = query.filter(BorrowRecord.status == BorrowStatus(status_filter))
        except ValueError:
            pass
    if keyword:
        query = query.join(BorrowRecord.user).join(BookCopy).join(Book).filter(
            or_(
                User.username.contains(keyword),
                Book.title.contains(keyword)
            )
        )

    total = query.count()
    borrows = query.order_by(BorrowRecord.borrow_date.desc())\
        .offset((page - 1) * size)\
        .limit(size)\
        .all()

    # 组装响应数据
    items = []
    for b in borrows:
        user_info = db.query(User).filter(User.user_id == b.user_id).first()
        copy_info = db.query(BookCopy).filter(BookCopy.copy_id == b.copy_id).first()
        book_info = db.query(Book).filter(Book.book_id == copy_info.book_id).first() if copy_info else None

        items.append({
            "borrow_id": b.borrow_id,
            "user_id": b.user_id,
            "username": user_info.username if user_info else "未知",
            "copy_id": b.copy_id,
            "barcode": copy_info.barcode if copy_info else "",
            "book_id": book_info.book_id if book_info else None,
            "title": book_info.title if book_info else "未知图书",
            "author": book_info.author if book_info else "",
            "borrow_date": b.borrow_date.strftime("%Y-%m-%d %H:%M") if b.borrow_date else "",
            "due_date": b.due_date.strftime("%Y-%m-%d") if b.due_date else "",
            "return_date": b.return_date.strftime("%Y-%m-%d %H:%M") if b.return_date else None,
            "return_branch": b.return_branch or None,
            "status": b.status.value,
            "status_text": _get_status_text(b.status.value),
            "fine_amount": round(b.fine_amount, 2) if b.fine_amount else 0,
            "renew_count": b.renew_count or 0,
            "is_overdue": b.status == BorrowStatus.ACTIVE and b.due_date < datetime.now(),
            "overdue_days": max(0, (datetime.now() - b.due_date).days) if b.due_date and b.due_date < datetime.now() else 0
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


@router.get("/users/{user_id}", response_model=dict)
async def get_user_borrows(
    user_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询指定用户的借阅记录"""
    if current_user.role.value != UserRole.SUPER_ADMIN.value and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权查看他人借阅记录")

    query = db.query(BorrowRecord).filter(BorrowRecord.user_id == user_id)
    total = query.count()
    borrows = query.order_by(BorrowRecord.borrow_date.desc()).offset((page - 1) * size).limit(size).all()

    items = []
    for b in borrows:
        copy_info = db.query(BookCopy).filter(BookCopy.copy_id == b.copy_id).first()
        book_info = db.query(Book).filter(Book.book_id == copy_info.book_id).first() if copy_info else None

        items.append({
            "borrow_id": b.borrow_id,
            "copy_id": b.copy_id,
            "title": book_info.title if book_info else "未知",
            "author": book_info.author if book_info else "",
            "borrow_date": b.borrow_date.strftime("%Y-%m-%d") if b.borrow_date else "",
            "due_date": b.due_date.strftime("%Y-%m-%d") if b.due_date else "",
            "return_date": b.return_date.strftime("%Y-%m-%d") if b.return_date else None,
            "status": b.status.value,
            "fine_amount": round(b.fine_amount, 2) if b.fine_amount else 0,
            "renew_count": b.renew_count or 0
        })

    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "size": size
        }
    }


@router.get("/{borrow_id}", response_model=dict)
async def get_borrow_detail(
    borrow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取借阅记录详情"""
    borrow = db.query(BorrowRecord).filter(BorrowRecord.borrow_id == borrow_id).first()
    if not borrow:
        raise HTTPException(status_code=404, detail="借阅记录不存在")

    # 权限
    if current_user.role.value not in [UserRole.SUPER_ADMIN.value, UserRole.CIRCULATION_ADMIN.value]:
        if borrow.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="无权查看此借阅记录")

    user_info = db.query(User).filter(User.user_id == borrow.user_id).first()
    copy_info = db.query(BookCopy).filter(BookCopy.copy_id == borrow.copy_id).first()
    book_info = db.query(Book).filter(Book.book_id == copy_info.book_id).first() if copy_info else None
    operator_info = db.query(User).filter(User.user_id == borrow.operator_id).first() if borrow.operator_id else None

    return {
        "code": 200,
        "data": {
            "borrow_id": borrow.borrow_id,
            "user": {
                "user_id": user_info.user_id,
                "username": user_info.username,
                "reader_card_number": user_info.reader_card_number
            } if user_info else None,
            "book": {
                "book_id": book_info.book_id,
                "title": book_info.title,
                "author": book_info.author,
                "isbn": book_info.isbn
            } if book_info else None,
            "copy": {
                "copy_id": copy_info.copy_id,
                "barcode": copy_info.barcode
            } if copy_info else None,
            "borrow_date": borrow.borrow_date.isoformat() if borrow.borrow_date else None,
            "due_date": borrow.due_date.isoformat() if borrow.due_date else None,
            "return_date": borrow.return_date.isoformat() if borrow.return_date else None,
            "return_branch": borrow.return_branch or None,
            "status": borrow.status.value,
            "fine_amount": borrow.fine_amount,
            "renew_count": borrow.renew_count,
            "operator": operator_info.username if operator_info else None,
            "created_at": borrow.created_at.isoformat() if borrow.created_at else None
        }
    }


@router.get("/{borrow_id}/overdue-info", response_model=dict)
async def get_overdue_info(
    borrow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取借阅逾期信息"""
    borrow = db.query(BorrowRecord).filter(BorrowRecord.borrow_id == borrow_id).first()
    if not borrow:
        raise HTTPException(status_code=404, detail="借阅记录不存在")

    now = datetime.now()
    is_overdue = borrow.status == BorrowStatus.ACTIVE and borrow.due_date < now

    result = {
        "borrow_id": borrow.borrow_id,
        "is_overdue": is_overdue,
        "due_date": borrow.due_date.strftime("%Y-%m-%d") if borrow.due_date else None,
        "current_date": now.strftime("%Y-%m-%d"),
    }

    if is_overdue:
        total_overdue_days = (now - borrow.due_date).days
        grace_days = settings.FINE_GRACE_DAYS
        chargeable_days = max(0, total_overdue_days - grace_days)
        fine_amount = chargeable_days * settings.DAILY_FINE_AMOUNT

        result.update({
            "total_overdue_days": total_overdue_days,
            "grace_days": grace_days,
            "chargeable_days": chargeable_days,
            "daily_fine_rate": settings.DAILY_FINE_AMOUNT,
            "estimated_fine": round(fine_amount, 2)
        })
    else:
        days_remaining = (borrow.due_date - now).days if borrow.due_date else 0
        result["days_remaining"] = max(0, days_remaining)

    return {"code": 200, "data": result}


# ============ 辅助函数 ============

def _get_status_text(status: str) -> str:
    """状态中文映射"""
    mapping = {
        "active": "借阅中",
        "returned": "已归还",
        "overdue": "逾期",
        "lost": "丢失"
    }
    return mapping.get(status, status)
