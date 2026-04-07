"""
图书管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, delete
from typing import Optional
from app.core.database import get_db
from app.models.models import (
    Book, BookCopy, Category, BookStatus, CopyStatus,
    BookComment, BookRating, Reservation
)
from app.schemas.schemas import BookCreate, BookUpdate, BookResponse, BookSearch, PaginationResponse
from app.api.dependencies import require_admin, require_catalog_admin
from app.models.models import User
import math

router = APIRouter(prefix="/books", tags=["图书管理"])

@router.get("", response_model=dict)
async def get_books(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    title: Optional[str] = None,
    author: Optional[str] = None,
    isbn: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """分页查询图书列表"""
    query = db.query(Book)
    
    # 条件筛选
    if title:
        query = query.filter(Book.title.contains(title))
    if author:
        query = query.filter(Book.author.contains(author))
    if isbn:
        query = query.filter(Book.isbn == isbn)
    if category_id:
        query = query.filter(Book.category_id == category_id)
    if status:
        query = query.filter(Book.status == status)
    
    # 总数
    total = query.count()
    pages = math.ceil(total / size)
    
    # 分页
    books = query.offset((page - 1) * size).limit(size).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [BookResponse.model_validate(book.__dict__) for book in books],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    }

@router.get("/search", response_model=dict)
async def search_books(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """多条件检索图书"""
    search_query = db.query(Book).filter(
        or_(
            Book.title.contains(query),
            Book.author.contains(query),
            Book.isbn.contains(query),
            Book.description.contains(query)
        )
    )
    
    total = search_query.count()
    pages = math.ceil(total / size)
    
    books = search_query.offset((page - 1) * size).limit(size).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [BookResponse.model_validate(book.__dict__) for book in books],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    }

@router.get("/{book_id}", response_model=dict)
async def get_book(book_id: int, db: Session = Depends(get_db)):
    """查询单本图书详情（含分类名、副本列表）"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图书不存在"
        )

    book_data = BookResponse.model_validate(book.__dict__).model_dump()

    # 附加分类名称
    if book.category_id:
        category = db.query(Category).filter(Category.category_id == book.category_id).first()
        book_data["category_name"] = category.name if category else ""
    else:
        book_data["category_name"] = ""

    # 附加副本列表
    copies = db.query(BookCopy).filter(BookCopy.book_id == book_id).all()
    book_data["copies"] = [
        {
            "copy_id": c.copy_id,
            "barcode": c.barcode,
            "status": c.status.value,
            "location_detail": c.location_detail,
        }
        for c in copies
    ]

    return {"code": 200, "data": book_data}

@router.post("", response_model=BookResponse)
async def create_book(
    book_data: BookCreate,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    """添加图书"""
    # 检查ISBN是否已存在
    if book_data.isbn:
        existing_book = db.query(Book).filter(Book.isbn == book_data.isbn).first()
        if existing_book:
            # 如果ISBN已存在，增加副本数
            existing_book.total_copies += book_data.total_copies
            existing_book.available_copies += book_data.total_copies
            db.commit()
            db.refresh(existing_book)
            return existing_book
    
    # 创建新图书记录
    new_book = Book(
        isbn=book_data.isbn,
        title=book_data.title,
        author=book_data.author,
        publisher=book_data.publisher,
        publish_year=book_data.publish_year,
        category_id=book_data.category_id,
        location=book_data.location,
        price=book_data.price,
        cover_url=book_data.cover_url,
        description=book_data.description,
        call_number=book_data.call_number,
        total_copies=book_data.total_copies,
        available_copies=book_data.total_copies,
        status=BookStatus.AVAILABLE
    )
    
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    
    # 创建单册副本
    for i in range(book_data.total_copies):
        barcode = f"{book_data.isbn or 'ISBN'}-{new_book.book_id}-{i+1:03d}"
        copy = BookCopy(
            book_id=new_book.book_id,
            barcode=barcode,
            status=CopyStatus.AVAILABLE,
            location_detail=book_data.location
        )
        db.add(copy)
    
    db.commit()
    db.refresh(new_book)
    
    return new_book

@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_data: BookUpdate,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    """更新图书信息"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图书不存在"
        )
    
    # 更新字段
    update_data = book_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(book, key, value)
    
    db.commit()
    db.refresh(book)
    
    return book

@router.delete("/{book_id}")
async def delete_book(
    book_id: int,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    """删除图书（逻辑删除）"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图书不存在"
        )
    
    # 检查是否有借阅中的副本
    if book.available_copies < book.total_copies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="存在未归还的图书副本，无法删除"
        )
    
    # 逻辑删除：标记为下架
    book.status = BookStatus.WITHDRAWN
    db.commit()
    
    return {"code": 200, "message": "图书已删除"}

@router.delete("/{book_id}/physical")
async def physical_delete_book(
    book_id: int,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    """物理删除图书（从数据库永久移除）"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图书不存在"
        )

    # 检查是否有借阅中的副本
    borrowed_copies = db.query(BookCopy).filter(
        BookCopy.book_id == book_id,
        BookCopy.status.in_([CopyStatus.BORROWED, CopyStatus.RESERVED])
    ).count()
    if borrowed_copies > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"仍有 {borrowed_copies} 本副本借出或被预约，无法物理删除"
        )

    # 删除关联的副本记录
    db.query(BookCopy).filter(BookCopy.book_id == book_id).delete()

    # 删除关联的评论、评分、预约（忽略表不存在的情况）
    from sqlalchemy.exc import OperationalError
    for table in [BookComment, BookRating, Reservation]:
        try:
            db.execute(delete(table.__table__).where(table.book_id == book_id))
        except OperationalError:
            pass

    # 删除图书主记录
    db.delete(book)

    # 写入审计日志
    from app.core.audit_log import write_log
    write_log(db, current_user.user_id, "book:physical_delete", "Book", book_id,
              before_data={"title": book.title, "isbn": book.isbn, "author": book.author})
    db.commit()

    return {"code": 200, "message": f"图书「{book.title}」已永久删除"}

@router.post("/{book_id}/copies", response_model=dict)
async def add_book_copies(
    book_id: int,
    copies_count: int,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    """添加图书副本"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图书不存在"
        )
    
    # 创建新副本
    for i in range(copies_count):
        barcode = f"{book.isbn or 'ISBN'}-{book_id}-{book.total_copies + i + 1:03d}"
        copy = BookCopy(
            book_id=book_id,
            barcode=barcode,
            status=CopyStatus.AVAILABLE,
            location_detail=book.location
        )
        db.add(copy)
    
    # 更新图书副本数
    book.total_copies += copies_count
    book.available_copies += copies_count
    
    db.commit()
    
    return {
        "code": 200,
        "message": f"成功添加{copies_count}个副本",
        "data": {
            "total_copies": book.total_copies,
            "available_copies": book.available_copies
        }
    }
