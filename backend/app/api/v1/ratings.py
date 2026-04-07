"""
图书评分、评论与个性化推荐路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, case, literal_column
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.models.models import (
    BookRating, BookComment, Book, Category, User,
    BorrowRecord, PurchaseRequest, CommentStatus,
    UserRole, BorrowStatus, PurchaseRequestStatus, BookStatus,
)
from app.schemas.schemas import (
    BookRatingCreate, BookRatingResponse,
    BookCommentCreate, BookCommentUpdate, BookCommentResponse,
)
from app.api.dependencies import get_current_user, require_admin

router = APIRouter(tags=["图书评分与评论"])


# ==================== 图书评分 ====================

@router.post("/books/{book_id}/ratings", response_model=BookRatingResponse)
async def rate_book(
    book_id: int,
    rating_data: BookRatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读者对图书评分（1-5星）"""
    # 检查图书是否存在
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")

    # 检查是否已评分（更新已有评分）
    existing = db.query(BookRating).filter(
        and_(BookRating.user_id == current_user.user_id, BookRating.book_id == book_id)
    ).first()

    if existing:
        existing.rating = rating_data.rating
        db.commit()
        db.refresh(existing)
        return existing

    new_rating = BookRating(
        user_id=current_user.user_id,
        book_id=book_id,
        rating=rating_data.rating,
    )
    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)
    return new_rating


@router.get("/books/{book_id}/ratings", response_model=dict)
async def get_book_ratings(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取某书的评分列表和统计"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")

    # 评分统计
    stats = db.query(
        func.count(BookRating.rating_id).label('total'),
        func.avg(BookRating.rating).label('average'),
    ).filter(BookRating.book_id == book_id).first()

    total_ratings = stats.total or 0
    avg_rating = round(float(stats.average), 1) if stats.average else 0.0

    # 分布统计（1-5星各多少）
    distribution = {}
    for i in range(1, 6):
        count = db.query(func.count()).filter(
            and_(BookRating.book_id == book_id, BookRating.rating == i)
        ).scalar() or 0
        distribution[str(i)] = count

    # 我的评分
    my_rating = None
    user_rating = db.query(BookRating).filter(
        and_(BookRating.user_id == current_user.user_id, BookRating.book_id == book_id)
    ).first()
    if user_rating:
        my_rating = user_rating.rating

    return {
        "code": 200, "message": "success",
        "data": {
            "book_id": book_id,
            "total_ratings": total_ratings,
            "average_rating": avg_rating,
            "distribution": distribution,
            "my_rating": my_rating,
        }
    }


@router.get("/books/{book_id}/comments", response_model=dict)
async def get_book_comments(
    book_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取某书公开评论列表"""
    query = db.query(BookComment).filter(
        and_(
            BookComment.book_id == book_id,
            BookComment.status == CommentStatus.APPROVED,
        )
    )

    total = query.count()
    comments = query.order_by(desc(BookComment.created_at)).offset((page - 1) * size).limit(size).all()

    items = []
    for c in comments:
        u = db.query(User).filter(User.user_id == c.user_id).first()
        item = BookCommentResponse.model_validate(c.__dict__).model_dump()
        item["username"] = u.username if u else "未知用户"
        items.append(item)

    return {
        "code": 200, "message": "success",
        "data": {"items": items, "total": total, "page": page, "size": size}
    }


@router.post("/books/{book_id}/comments", response_model=BookCommentResponse)
async def comment_on_book(
    book_id: int,
    comment_data: BookCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读者发表评论"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")

    # 检查用户是否借阅过该书（业务规则：仅借阅过的读者可评论）
    from app.models.models import BookCopy as BC2
    has_borrowed = db.query(BorrowRecord).join(BC2, BorrowRecord.copy_id == BC2.copy_id).filter(
        and_(
            BorrowRecord.user_id == current_user.user_id,
            BC2.book_id == book_id,
        )
    ).first()

    comment = BookComment(
        user_id=current_user.user_id,
        book_id=book_id,
        content=comment_data.content,
        status=CommentStatus.PENDING,  # 默认待审核
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    resp = BookCommentResponse.model_validate(comment.__dict__)
    return resp


@router.put("/comments/{comment_id}")
async def moderate_comment(
    comment_id: int,
    mod_data: BookCommentUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理员审核评论（通过/隐藏/拒绝）"""
    comment = db.query(BookComment).filter(BookComment.comment_id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    if mod_data.status:
        valid_statuses = [s.value for s in CommentStatus]
        if mod_data.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"无效状态，可选值: {valid_statuses}")
        comment.status = CommentStatus(mod_data.status)

    if mod_data.admin_reply is not None:
        comment.admin_reply = mod_data.admin_reply

    db.commit()
    db.refresh(comment)

    u = db.query(User).filter(User.user_id == comment.user_id).first()
    item = BookCommentResponse.model_validate(comment.__dict__).model_dump()
    item["username"] = u.username if u else "未知"
    return {"code": 200, "message": "操作成功", "data": item}


# ==================== 个性化推荐 ====================

@router.get("/recommendations/personalized", response_model=dict)
async def get_personalized_recommendations(
    limit: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """基于借阅历史的个性化推荐（同类别未读图书）"""

    # 获取用户已借阅的图书ID
    borrowed_books = db.query(BorrowRecord.copy_id).filter(
        BorrowRecord.user_id == current_user.user_id
    ).distinct().all()
    borrowed_copy_ids = set(b.copy_id for b in borrowed_books)

    if not borrowed_copy_ids:
        # 无借阅历史 → 返回热门图书
        from app.models.models import BookCopy
        hot_books = db.query(
            Book.book_id, Book.title, Book.author, Book.cover_url,
            func.count(BorrowRecord.borrow_id).label('borrow_count')
        ).outerjoin(BookCopy, Book.book_id == BookCopy.book_id).outerjoin(
            BorrowRecord, BookCopy.copy_id == BorrowRecord.copy_id
        ).group_by(Book.book_id).order_by(
            desc(func.count(BorrowRecord.borrow_id))
        ).limit(limit).all()

        return {
            "code": 200, "message": "success",
            "data": {
                "type": "popular",
                "items": [
                    {"book_id": b.book_id, "title": b.title, "author": b.author,
                     "cover_url": b.cover_url, "reason": f"热门图书 (已借{b.borrow_count}次)"}
                    for b in hot_books
                ]
            }
        }

    # 通过副本找到用户借过的图书，再获取这些图书的分类
    from app.models.models import BookCopy as BC
    borrowed_book_ids_query = db.query(BC.book_id).filter(BC.copy_id.in_(borrowed_copy_ids)).distinct()
    borrowed_book_ids = set(r[0] for r in borrowed_book_ids_query.all())

    # 统计用户借阅最多的分类
    category_stats = db.query(
        Book.category_id, func.count(Book.book_id).label('cnt')
    ).filter(Book.book_id.in_(borrowed_book_ids)).group_by(
        Book.category_id
    ).order_by(desc('cnt')).limit(3).all()

    preferred_category_ids = [c.category_id for c in category_stats if c.category_id]

    if not preferred_category_ids:
        preferred_category_ids = []

    # 推荐同类别但未借阅的图书
    recommended = db.query(Book).filter(
        and_(
            Book.category_id.in_(preferred_category_ids) if preferred_category_ids else True,
            ~Book.book_id.in_(borrowed_book_ids),
            Book.status.in_(['available', 'borrowed']),
        )
    ).order_by(
        case(
            (Book.available_copies > 0, 0),
            else_=1,
        ),
        desc(Book.created_at),
    ).limit(limit).all()

    items = []
    for b in recommended:
        cat_name = ""
        if b.category_id:
            cat = db.query(Category).filter(Category.category_id == b.category_id).first()
            cat_name = cat.name if cat else ""

        items.append({
            "book_id": b.book_id,
            "title": b.title,
            "author": b.author,
            "cover_url": b.cover_url,
            "category_name": cat_name,
            "available_copies": b.available_copies,
            "reason": f"基于您偏好的「{cat_name}」类别推荐" if cat_name else "为您精选",
        })

    return {
        "code": 200, "message": "success",
        "data": {
            "type": "personalized",
            "preferred_categories": [
                db.query(Category).filter(Category.category_id == cid).first().name
                for cid in preferred_category_ids
            ],
            "items": items,
        }
    }


@router.get("/recommendations/new-books", response_model=dict)
async def get_new_arrivals(
    days: int = Query(30, ge=7, le=180),
    limit: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新书上架推荐"""
    cutoff = datetime.now() - timedelta(days=days)

    new_books = db.query(Book).filter(
        and_(
            Book.created_at >= cutoff,
            Book.status != BookStatus.WITHDRAWN.value,
        )
    ).order_by(desc(Book.created_at)).limit(limit).all()

    items = []
    for b in new_books:
        cat_name = ""
        if b.category_id:
            cat = db.query(Category).filter(Category.category_id == b.category_id).first()
            cat_name = cat.name if cat else ""

        items.append({
            "book_id": b.book_id,
            "title": b.title,
            "author": b.author,
            "cover_url": b.cover_url,
            "category_name": cat_name,
            "isbn": b.isbn,
            "publisher": b.publisher,
            "created_at": b.created_at.strftime("%Y-%m-%d") if b.created_at else "",
            "available_copies": b.available_copies,
        })

    return {
        "code": 200, "message": "success",
        "data": {"days": days, "total": len(items), "items": items}
    }


@router.get("/recommendations/hot", response_model=dict)
async def get_hot_books(
    days: int = Query(90, ge=30, le=365),
    limit: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """热门图书排行榜（按借阅次数）"""
    from app.models.models import BookCopy as BC

    start_date = datetime.now() - timedelta(days=days)

    hot_books = db.query(
        Book.book_id, Book.title, Book.author, Book.cover_url,
        func.count(BorrowRecord.borrow_id).label('borrow_count'),
    ).join(BC, Book.book_id == BC.book_id).join(
        BorrowRecord, BC.copy_id == BorrowRecord.copy_id
    ).filter(
        BorrowRecord.borrow_date >= start_date
    ).group_by(Book.book_id).order_by(
        desc(func.count(BorrowRecord.borrow_id))
    ).limit(limit).all()

    items = [
        {"rank": i + 1, "book_id": b.book_id, "title": b.title, "author": b.author,
         "cover_url": b.cover_url, "borrow_count": b.borrow_count}
        for i, b in enumerate(hot_books)
    ]

    return {
        "code": 200, "message": "success",
        "data": {"period_days": days, "items": items}
    }
