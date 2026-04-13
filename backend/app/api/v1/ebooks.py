"""
电子书管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.core.database import get_db
from app.models.models import (
    EBook, EBookBorrowRecord, Category, BookStatus, BorrowStatus
)
from app.schemas.schemas import EBookCreate, EBookUpdate, EBookResponse, PaginationResponse
from app.api.dependencies import require_admin, require_catalog_admin, get_current_user
from app.models.models import User
import math

router = APIRouter(prefix="/ebooks", tags=["电子书管理"])

@router.get("", response_model=dict)
async def get_ebooks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    title: Optional[str] = None,
    author: Optional[str] = None,
    isbn: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """分页查询电子书列表"""
    query = db.query(EBook)
    
    # 条件筛选
    if title:
        query = query.filter(EBook.title.contains(title))
    if author:
        query = query.filter(EBook.author.contains(author))
    if isbn:
        query = query.filter(EBook.isbn == isbn)
    if category_id:
        query = query.filter(EBook.category_id == category_id)
    if status:
        query = query.filter(EBook.status == status)
    
    # 总数
    total = query.count()
    pages = math.ceil(total / size)
    
    # 分页
    ebooks = query.offset((page - 1) * size).limit(size).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [EBookResponse.model_validate(ebook.__dict__) for ebook in ebooks],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    }

@router.get("/search", response_model=dict)
async def search_ebooks(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """多条件检索电子书"""
    search_query = db.query(EBook).filter(
        or_(
            EBook.title.contains(query),
            EBook.author.contains(query),
            EBook.isbn.contains(query),
            EBook.description.contains(query)
        )
    )
    
    total = search_query.count()
    pages = math.ceil(total / size)
    
    ebooks = search_query.offset((page - 1) * size).limit(size).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [EBookResponse.model_validate(ebook.__dict__) for ebook in ebooks],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    }

@router.get("/{ebook_id}", response_model=dict)
async def get_ebook(ebook_id: int, db: Session = Depends(get_db)):
    """查询单本电子书详情（含分类名）"""
    ebook = db.query(EBook).filter(EBook.ebook_id == ebook_id).first()
    if not ebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="电子书不存在"
        )

    ebook_data = EBookResponse.model_validate(ebook.__dict__).model_dump()

    # 附加分类名称
    if ebook.category_id:
        category = db.query(Category).filter(Category.category_id == ebook.category_id).first()
        ebook_data["category_name"] = category.name if category else ""
    else:
        ebook_data["category_name"] = ""

    return {"code": 200, "data": ebook_data}

@router.post("", response_model=EBookResponse)
async def create_ebook(
    ebook_data: EBookCreate,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    """添加电子书"""
    # 检查ISBN是否已存在
    if ebook_data.isbn:
        existing_ebook = db.query(EBook).filter(EBook.isbn == ebook_data.isbn).first()
        if existing_ebook:
            # 如果ISBN已存在，增加副本数
            existing_ebook.total_copies += ebook_data.total_copies
            existing_ebook.available_copies += ebook_data.total_copies
            db.commit()
            db.refresh(existing_ebook)
            return existing_ebook
    
    # 创建新电子书记录
    new_ebook = EBook(
        isbn=ebook_data.isbn,
        title=ebook_data.title,
        author=ebook_data.author,
        publisher=ebook_data.publisher,
        publish_year=ebook_data.publish_year,
        category_id=ebook_data.category_id,
        file_format=ebook_data.file_format,
        file_size=ebook_data.file_size,
        file_path=ebook_data.file_path,
        cover_url=ebook_data.cover_url,
        description=ebook_data.description,
        call_number=ebook_data.call_number,
        total_copies=ebook_data.total_copies,
        available_copies=ebook_data.total_copies,
        status=BookStatus.AVAILABLE
    )
    
    db.add(new_ebook)
    db.commit()
    db.refresh(new_ebook)
    
    return new_ebook

@router.put("/{ebook_id}", response_model=EBookResponse)
async def update_ebook(
    ebook_id: int,
    ebook_data: EBookUpdate,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    """更新电子书信息"""
    ebook = db.query(EBook).filter(EBook.ebook_id == ebook_id).first()
    if not ebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="电子书不存在"
        )
    
    # 更新字段
    update_data = ebook_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ebook, key, value)
    
    db.commit()
    db.refresh(ebook)
    
    return ebook

@router.delete("/{ebook_id}")
async def delete_ebook(
    ebook_id: int,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    """删除电子书（逻辑删除）"""
    ebook = db.query(EBook).filter(EBook.ebook_id == ebook_id).first()
    if not ebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="电子书不存在"
        )
    
    # 检查是否有借阅中的副本
    if ebook.available_copies < ebook.total_copies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="存在未归还的电子书副本，无法删除"
        )
    
    # 逻辑删除：标记为下架
    ebook.status = BookStatus.WITHDRAWN
    db.commit()
    
    return {"code": 200, "message": "电子书已删除"}

@router.post("/{ebook_id}/borrow")
async def borrow_ebook(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """借阅电子书"""
    ebook = db.query(EBook).filter(EBook.ebook_id == ebook_id).first()
    if not ebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="电子书不存在"
        )
    
    # 检查是否可借
    if ebook.available_copies <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="电子书已借完"
        )
    
    # 检查用户是否有未归还的电子书
    active_borrows = db.query(EBookBorrowRecord).filter(
        EBookBorrowRecord.user_id == current_user.user_id,
        EBookBorrowRecord.status == BorrowStatus.ACTIVE
    ).count()
    
    if active_borrows >= current_user.max_borrow_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"已达到最大借阅数量（{current_user.max_borrow_count}本）"
        )
    
    # 创建借阅记录
    from datetime import datetime, timedelta
    due_date = datetime.utcnow() + timedelta(days=current_user.borrow_limit_days)
    
    borrow_record = EBookBorrowRecord(
        user_id=current_user.user_id,
        ebook_id=ebook_id,
        due_date=due_date,
        status=BorrowStatus.ACTIVE
    )
    
    # 减少可用副本数
    ebook.available_copies -= 1
    
    db.add(borrow_record)
    db.commit()
    db.refresh(borrow_record)
    
    return {
        "code": 200,
        "message": "借阅成功",
        "data": {
            "borrow_id": borrow_record.borrow_id,
            "ebook_id": ebook_id,
            "due_date": due_date
        }
    }

@router.post("/{ebook_id}/return")
async def return_ebook(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """归还电子书"""
    # 查找用户的活跃借阅记录
    borrow_record = db.query(EBookBorrowRecord).filter(
        EBookBorrowRecord.user_id == current_user.user_id,
        EBookBorrowRecord.ebook_id == ebook_id,
        EBookBorrowRecord.status == BorrowStatus.ACTIVE
    ).first()
    
    if not borrow_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到该电子书的借阅记录"
        )
    
    # 更新借阅记录
    from datetime import datetime
    borrow_record.return_date = datetime.utcnow()
    borrow_record.status = BorrowStatus.RETURNED
    
    # 增加可用副本数
    ebook = db.query(EBook).filter(EBook.ebook_id == ebook_id).first()
    ebook.available_copies += 1
    
    db.commit()
    
    return {
        "code": 200,
        "message": "归还成功"
    }

@router.get("/user/borrowed", response_model=dict)
async def get_user_borrowed_ebooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户已借阅的电子书"""
    borrow_records = db.query(EBookBorrowRecord).filter(
        EBookBorrowRecord.user_id == current_user.user_id,
        EBookBorrowRecord.status == BorrowStatus.ACTIVE
    ).all()
    
    ebooks = []
    for record in borrow_records:
        ebook = db.query(EBook).filter(EBook.ebook_id == record.ebook_id).first()
        if ebook:
            ebook_data = EBookResponse.model_validate(ebook.__dict__).model_dump()
            ebook_data["borrow_date"] = record.borrow_date
            ebook_data["due_date"] = record.due_date
            ebooks.append(ebook_data)
    
    return {
        "code": 200,
        "data": ebooks
    }
