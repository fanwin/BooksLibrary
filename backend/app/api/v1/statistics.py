"""
统计分析路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, case
from datetime import datetime, timedelta
from typing import Optional
import csv
import io

from app.core.database import get_db
from app.models.models import (
    BorrowRecord, Book, Category, User, Fine, SystemLog, BookCopy,
    BorrowStatus, FineStatus, UserRole
)
from app.schemas.schemas import DashboardStats, BorrowTrendData, HotBookData, CategoryStatData
from app.api.dependencies import require_admin, require_auditor, get_current_user

router = APIRouter(prefix="/statistics", tags=["统计分析"])

@router.get("/dashboard", response_model=dict)
async def get_dashboard_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取运营看板数据"""
    today = datetime.now().date()

    # ========== 基础当日统计 ==========
    today_borrows = db.query(BorrowRecord).filter(
        func.date(BorrowRecord.borrow_date) == today
    ).count()

    today_returns = db.query(BorrowRecord).filter(
        func.date(BorrowRecord.return_date) == today
    ).count()

    today_fines = db.query(Fine).filter(
        and_(Fine.status == FineStatus.PAID, func.date(Fine.paid_date) == today)
    ).with_entities(func.sum(Fine.amount)).scalar() or 0

    total_borrowed = db.query(BorrowRecord).filter(
        BorrowRecord.status == BorrowStatus.ACTIVE
    ).count()

    total_overdue = db.query(BorrowRecord).filter(
        and_(BorrowRecord.status == BorrowStatus.ACTIVE, BorrowRecord.due_date < datetime.now())
    ).count()

    from app.models.models import Reservation, ReservationStatus
    total_reservations = db.query(Reservation).filter(
        Reservation.status == ReservationStatus.PENDING
    ).count()

    total_books = db.query(Book).count()
    total_copies = db.query(Book).with_entities(func.sum(Book.total_copies)).scalar() or 0
    total_readers = db.query(User).filter(User.role == UserRole.READER).count()

    # 图书流通率（借阅次数 / 总馆藏副本数）
    total_borrow_count = db.query(BorrowRecord).count()
    circulation_rate = round(total_borrow_count / total_copies * 100, 2) if total_copies > 0 else 0

    # 罚款总数（历史累计已缴罚款金额）
    total_fines_amount = db.query(Fine).filter(
        Fine.status == FineStatus.PAID
    ).with_entities(func.sum(Fine.amount)).scalar() or 0

    # ========== Phase2: 周期性统计 & 环比增长 ==========
    import calendar

    # 本周借阅（本周一 ~ 今天）
    week_start = today - timedelta(days=today.weekday())
    week_borrows = db.query(BorrowRecord).filter(
        func.date(BorrowRecord.borrow_date) >= week_start,
        func.date(BorrowRecord.borrow_date) <= today
    ).count()

    # 上周借阅（上周一 ~ 上周日）→ 用于计算周环比
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start - timedelta(days=1)
    last_week_borrows = db.query(BorrowRecord).filter(
        func.date(BorrowRecord.borrow_date) >= last_week_start,
        func.date(BorrowRecord.borrow_date) <= last_week_end
    ).count()
    if last_week_borrows > 0:
        week_growth = round((week_borrows - last_week_borrows) / last_week_borrows * 100, 1)
    else:
        week_growth = 100.0 if week_borrows > 0 else 0.0

    # 本月借阅
    month_start = today.replace(day=1)
    month_borrows = db.query(BorrowRecord).filter(
        func.date(BorrowRecord.borrow_date) >= month_start,
        func.date(BorrowRecord.borrow_date) <= today
    ).count()

    # 上月借阅 → 用于计算月环比
    if today.month == 1:
        last_month_start = today.replace(year=today.year - 1, month=12, day=1)
    else:
        last_month_start = today.replace(month=today.month - 1, day=1)
    _, last_day_of_last_month = calendar.monthrange(last_month_start.year, last_month_start.month)
    last_month_end = last_month_start.replace(day=last_day_of_last_month)
    last_month_borrows = db.query(BorrowRecord).filter(
        func.date(BorrowRecord.borrow_date) >= last_month_start,
        func.date(BorrowRecord.borrow_date) <= last_month_end
    ).count()
    if last_month_borrows > 0:
        month_growth = round((month_borrows - last_month_borrows) / last_month_borrows * 100, 1)
    else:
        month_growth = 100.0 if month_borrows > 0 else 0.0

    # ========== Phase2: 未缴罚款总额（管理员财务视角）==========
    unpaid_fines_total = db.query(Fine).filter(
        Fine.status == FineStatus.PENDING
    ).with_entities(func.sum(Fine.amount)).scalar() or 0

    # ========== Phase2: 今日新注册用户 ==========
    today_new_readers = db.query(User).filter(
        User.role == UserRole.READER,
        func.date(User.created_at) == today
    ).count()

    # ========== Phase1: 馆藏健康度 — 在馆率 ==========
    available_copies = db.query(Book).with_entities(func.sum(Book.available_copies)).scalar() or 0
    available_rate = round(available_copies / total_copies * 100, 2) if total_copies > 0 else 0

    # ========== Phase1: 沉睡图书数量（180天未被借阅）==========
    dormant_cutoff = datetime.now() - timedelta(days=180)
    dormant_subq = db.query(BorrowRecord.copy_id).filter(
        BorrowRecord.borrow_date >= dormant_cutoff
    )
    dormant_books_count = db.query(Book).filter(
        ~Book.book_id.in_(dormant_subq)
    ).count()

    return {
        "code": 200, "message": "success",
        "data": {
            # --- 当日核心 ---
            "today_borrows": today_borrows,
            "today_returns": today_returns,
            "today_fines": float(today_fines),
            "total_borrowed": total_borrowed,
            "total_overdue": total_overdue,
            "total_reservations": total_reservations,
            "total_books": total_books,
            "total_copies": total_copies,
            "total_readers": total_readers,

            # --- 累计指标 ---
            "total_borrow_count": total_borrow_count,
            "total_fines_amount": float(total_fines_amount),
            "circulation_rate": circulation_rate,

            # === Phase2: 周期统计 + 环比 ===
            "week_borrows": week_borrows,
            "month_borrows": month_borrows,
            "week_growth": week_growth,          # 周环比 %
            "month_growth": month_growth,         # 月环比 %

            # === Phase2: 财务 & 用户 ===
            "unpaid_fines_total": float(unpaid_fines_total),
            "today_new_readers": today_new_readers,

            # === Phase1: 馆藏健康度 ===
            "available_rate": available_rate,     # 在馆率 %
            "dormant_books_count": dormant_books_count,  # 沉睡图书本数
        }
    }


@router.get("/my-dashboard", response_model=dict)
async def get_my_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """读者个人看板 - 展示与当前用户相关的数据"""
    uid = current_user.user_id

    # 我当前借出中的数量
    my_borrowing = db.query(BorrowRecord).filter(
        BorrowRecord.user_id == uid,
        BorrowRecord.status == BorrowStatus.ACTIVE
    ).count()

    # 我逾期的数量
    my_overdue = db.query(BorrowRecord).filter(
        BorrowRecord.user_id == uid,
        BorrowRecord.status == BorrowStatus.ACTIVE,
        BorrowRecord.due_date < datetime.now()
    ).count()

    # 我的待处理预约
    from app.models.models import Reservation, ReservationStatus
    my_reservations = db.query(Reservation).filter(
        Reservation.user_id == uid,
        Reservation.status == ReservationStatus.PENDING
    ).count()

    # 我的未缴纳罚款
    my_unpaid_fines = db.query(Fine).filter(
        Fine.user_id == uid,
        Fine.status == FineStatus.PENDING
    ).count()
    my_fine_total = db.query(Fine).filter(
        Fine.user_id == uid,
        Fine.status == FineStatus.PENDING
    ).with_entities(func.sum(Fine.amount)).scalar() or 0

    # 我的历史借阅总数
    my_total_borrows = db.query(BorrowRecord).filter(
        BorrowRecord.user_id == uid
    ).count()

    return {
        "code": 200, "message": "success",
        "data": {
            "my_borrowing": my_borrowing,
            "my_overdue": my_overdue,
            "my_reservations": my_reservations,
            "my_unpaid_fines": my_unpaid_fines,
            "my_fine_total": float(my_fine_total),
            "my_total_borrows": my_total_borrows,
        }
    }

@router.get("/borrow-trend", response_model=dict)
async def get_borrow_trend(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    """借阅趋势统计"""
    start_date = datetime.now() - timedelta(days=days)
    
    # 按日期统计借阅量
    trend_data = db.query(
        func.date(BorrowRecord.borrow_date).label('date'),
        func.count(BorrowRecord.borrow_id).label('count')
    ).filter(
        BorrowRecord.borrow_date >= start_date
    ).group_by(
        func.date(BorrowRecord.borrow_date)
    ).order_by(
        func.date(BorrowRecord.borrow_date)
    ).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": [
            {"date": str(item.date), "count": item.count}
            for item in trend_data
        ]
    }

@router.get("/hot-books", response_model=dict)
async def get_hot_books(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    """热门图书排行"""
    start_date = datetime.now() - timedelta(days=days)
    
    # 按图书统计借阅次数
    hot_books = db.query(
        Book.book_id,
        Book.title,
        Book.author,
        func.count(BorrowRecord.borrow_id).label('borrow_count')
    ).join(
        BorrowRecord, Book.book_id == BorrowRecord.copy_id
    ).filter(
        BorrowRecord.borrow_date >= start_date
    ).group_by(
        Book.book_id, Book.title, Book.author
    ).order_by(
        func.count(BorrowRecord.borrow_id).desc()
    ).limit(limit).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": [
            {
                "book_id": item.book_id,
                "title": item.title,
                "author": item.author,
                "borrow_count": item.borrow_count
            }
            for item in hot_books
        ]
    }

@router.get("/category-distribution", response_model=dict)
async def get_category_distribution(
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    """分类借阅分布统计"""
    # 按分类统计图书数量和借阅次数
    category_stats = db.query(
        Category.name,
        func.count(Book.book_id).label('book_count'),
        func.count(BorrowRecord.borrow_id).label('borrow_count')
    ).outerjoin(
        Book, Category.category_id == Book.category_id
    ).outerjoin(
        BorrowRecord, Book.book_id == BorrowRecord.copy_id
    ).group_by(
        Category.name
    ).order_by(
        func.count(Book.book_id).desc()
    ).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": [
            {
                "category_name": item.name,
                "book_count": item.book_count,
                "borrow_count": item.borrow_count
            }
            for item in category_stats
        ]
    }

@router.get("/overdue-report", response_model=dict)
async def get_overdue_report(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """超期未还图书清单"""
    overdue_records = db.query(
        BorrowRecord,
        User.username,
        User.email,
        Book.title,
        Book.author
    ).join(
        User, BorrowRecord.user_id == User.user_id
    ).join(
        Book, BorrowRecord.copy_id == Book.book_id
    ).filter(
        and_(
            BorrowRecord.status == BorrowStatus.ACTIVE,
            BorrowRecord.due_date < datetime.now()
        )
    ).order_by(
        BorrowRecord.due_date
    ).all()
    
    result = []
    for borrow, username, email, title, author in overdue_records:
        overdue_days = (datetime.now() - borrow.due_date).days
        result.append({
            "borrow_id": borrow.borrow_id,
            "username": username,
            "email": email,
            "book_title": title,
            "author": author,
            "due_date": borrow.due_date,
            "overdue_days": overdue_days,
            "fine_amount": overdue_days * 0.5  # 假设每天0.5元
        })
    
    return {
        "code": 200,
        "message": "success",
        "data": result
    }

@router.get("/active-readers", response_model=dict)
async def get_active_readers(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    """活跃读者排行"""
    start_date = datetime.now() - timedelta(days=days)
    
    active_readers = db.query(
        User.user_id,
        User.username,
        func.count(BorrowRecord.borrow_id).label('borrow_count')
    ).join(
        BorrowRecord, User.user_id == BorrowRecord.user_id
    ).filter(
        BorrowRecord.borrow_date >= start_date
    ).group_by(
        User.user_id, User.username
    ).order_by(
        func.count(BorrowRecord.borrow_id).desc()
    ).limit(limit).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": [
            {
                "user_id": item.user_id,
                "username": item.username,
                "borrow_count": item.borrow_count
            }
            for item in active_readers
        ]
    }

@router.get("/dormant-books", response_model=dict)
async def get_dormant_books(
    days: int = Query(180, ge=1, le=730),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """长期未借阅图书分析（沉睡图书）"""
    start_date = datetime.now() - timedelta(days=days)
    
    # 查询在指定时间内没有被借阅过的图书
    dormant_books = db.query(Book).filter(
        ~Book.book_id.in_(
            db.query(BorrowRecord.copy_id).filter(
                BorrowRecord.borrow_date >= start_date
            )
        )
    ).limit(100).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "count": len(dormant_books),
            "books": [
                {
                    "book_id": book.book_id,
                    "title": book.title,
                    "author": book.author,
                    "total_copies": book.total_copies,
                    "available_copies": book.available_copies
                }
                for book in dormant_books
            ]
        }
    }


@router.get("/circulation-rate", response_model=dict)
async def get_circulation_rate(
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    """图书流通率统计（借阅次数/总馆藏）"""
    total_books = db.query(Book).count()
    total_copies = db.query(Book).with_entities(func.sum(Book.total_copies)).scalar() or 0
    total_borrowed = db.query(BorrowRecord).filter(
        BorrowRecord.status == BorrowStatus.ACTIVE
    ).count()
    total_borrow_history = db.query(BorrowRecord).count()

    # 各分类流通率
    category_circulation = db.query(
        Category.name,
        func.count(Book.book_id).label('book_count'),
        func.sum(Book.total_copies).label('total_copies'),
        func.count(BorrowRecord.borrow_id).label('borrow_times')
    ).outerjoin(
        Book, Category.category_id == Book.category_id
    ).outerjoin(
        BorrowRecord, Book.book_id == BorrowRecord.copy_id
    ).group_by(Category.name).all()

    category_data = []
    for item in category_circulation:
        copies = item.total_copies or 0
        rate = round(item.borrow_times / copies * 100, 2) if copies > 0 else 0
        category_data.append({
            "category_name": item.name or "未分类",
            "book_count": item.book_count,
            "total_copies": int(copies),
            "borrow_times": item.borrow_times,
            "circulation_rate": rate,
        })

    overall_rate = round(total_borrow_history / total_copies * 100, 2) if total_copies > 0 else 0

    return {
        "code": 200, "message": "success",
        "data": {
            "overall_rate": overall_rate,
            "total_books": total_books,
            "total_copies": total_copies,
            "currently_borrowed": total_borrowed,
            "total_borrow_history": total_borrow_history,
            "categories": category_data,
        }
    }


@router.get("/overdue-readers", response_model=dict)
async def get_overdue_readers(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """高频逾期读者列表 - 按当前逾期记录数排序"""
    now = datetime.now()

    overdue_reader_stats = db.query(
        User.user_id,
        User.username,
        User.email,
        func.count(BorrowRecord.borrow_id).label('overdue_count'),
        func.sum(
            case((BorrowRecord.due_date < now, 1), else_=0)
        ).label('overdue_days_total')
    ).join(
        BorrowRecord, User.user_id == BorrowRecord.user_id
    ).filter(
        and_(
            BorrowRecord.status == BorrowStatus.ACTIVE,
            BorrowRecord.due_date < now
        )
    ).group_by(
        User.user_id, User.username, User.email
    ).order_by(
        func.count(BorrowRecord.borrow_id).desc()
    ).limit(limit).all()

    result = []
    for item in overdue_reader_stats:
        # 计算该读者所有活跃借阅中的最大逾期天数
        max_overdue = db.query(
            func.max(func.julianday(now) - func.julianday(BorrowRecord.due_date))
        ).filter(
            and_(BorrowRecord.user_id == item.user_id,
                 BorrowRecord.status == BorrowStatus.ACTIVE,
                 BorrowRecord.due_date < now)
        ).scalar() or 0
        result.append({
            "user_id": item.user_id,
            "username": item.username,
            "email": item.email,
            "overdue_count": item.overdue_count,
            "max_overdue_days": int(max_overdue),
            "estimated_fine": round(item.overdue_days_total * 0.5, 2),
        })

    return {"code": 200, "message": "success", "data": result}


# ==================== 统计报表导出 ====================

@router.get("/export/borrow-report")
async def export_borrow_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    report_type: str = Query("monthly", description="monthly/yearly/custom"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """导出借阅统计报表为 CSV 格式"""
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "monthly":
        writer.writerow(["月份", "借阅量", "还书量", "新增读者", "罚款收入"])
        months = db.query(
            extract('year', BorrowRecord.borrow_date).label('year'),
            extract('month', BorrowRecord.borrow_date).label('month'),
        ).filter(BorrowRecord.borrow_date.isnot(None)).group_by(
            extract('year', BorrowRecord.borrow_date),
            extract('month', BorrowRecord.borrow_date),
        ).order_by(extract('year', BorrowRecord.borrow_date), extract('month', BorrowRecord.borrow_date)).all()

        for y, m in months:
            month_start = datetime(y, m, 1)
            import calendar
            _, last_day = calendar.monthrange(y, m)
            month_end = datetime(y, m, last_day, 23, 59, 59)

            borrows = db.query(BorrowRecord).filter(
                BorrowRecord.borrow_date >= month_start, BorrowRecord.borrow_date <= month_end
            ).count()
            returns_q = db.query(BorrowRecord).filter(
                BorrowRecord.return_date >= month_start, BorrowRecord.return_date <= month_end
            ).count()
            new_users = db.query(User).filter(
                User.created_at >= month_start, User.created_at <= month_end
            ).count()
            fines = db.query(Fine).filter(
                Fine.created_at >= month_start, Fine.created_at <= month_end
            ).with_entities(func.sum(Fine.amount)).scalar() or 0

            writer.writerow([f"{y}-{m:02d}", borrows, returns_q, new_users, round(fines, 2)])

    elif report_type == "yearly":
        writer.writerow(["年份", "总借阅", "总还书", "新增图书", "新增读者", "总收入"])
        years = db.query(extract('year', BorrowRecord.borrow_date)).distinct().all()
        for (y,) in years:
            y = int(y)
            year_start = datetime(y, 1, 1)
            year_end = datetime(y, 12, 31, 23, 59, 59)

            borrows = db.query(BorrowRecord).filter(
                BorrowRecord.borrow_date >= year_start, BorrowRecord.borrow_date <= year_end
            ).count()
            returns_q = db.query(BorrowRecord).filter(
                BorrowRecord.return_date >= year_start, BorrowRecord.return_date <= year_end
            ).count()
            new_books = db.query(Book).filter(
                Book.created_at >= year_start, Book.created_at <= year_end
            ).count()
            new_users = db.query(User).filter(
                User.created_at >= year_start, User.created_at <= year_end
            ).count()
            fines = db.query(Fine).filter(
                Fine.created_at >= year_start, Fine.created_at <= year_end
            ).with_entities(func.sum(Fine.amount)).scalar() or 0

            writer.writerow([y, borrows, returns_q, new_books, new_users, round(fines, 2)])

    elif report_type == "custom" and start_date and end_date:
        writer.writerow(["日期", "借阅用户", "图书名称", "作者", "状态", "应还日期", "实际归还"])
        records = db.query(
            BorrowRecord, User.username, Book.title, Book.author
        ).join(User, BorrowRecord.user_id == User.user_id).join(
            Book, BorrowRecord.copy_id == Book.book_id
        ).filter(BorrowRecord.borrow_date >= start_date, BorrowRecord.borrow_date <= end_date).order_by(
            BorrowRecord.borrow_date.desc()).limit(1000).all()

        for br, uname, title, author in records:
            writer.writerow([
                str(br.borrow_date)[:19], uname, title, author,
                br.status.value, str(br.due_date)[:19],
                str(br.return_date)[:19] if br.return_date else "",
            ])

    else:
        raise HTTPException(status_code=400, detail="请指定 report_type=monthly/yearly 并提供时间范围")

    output.seek(0)
    filename = f"library_report_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
