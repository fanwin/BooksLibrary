"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class UserRole(str, enum.Enum):
    """用户角色枚举"""
    SUPER_ADMIN = "super_admin"
    CATALOG_ADMIN = "catalog_admin"
    CIRCULATION_ADMIN = "circulation_admin"
    READER = "reader"
    AUDITOR = "auditor"

class UserStatus(str, enum.Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class BookStatus(str, enum.Enum):
    """图书状态枚举"""
    AVAILABLE = "available"
    BORROWED = "borrowed"
    RESERVED = "reserved"
    DAMAGED = "damaged"
    LOST = "lost"
    WITHDRAWN = "withdrawn"

class CopyStatus(str, enum.Enum):
    """单册状态枚举"""
    AVAILABLE = "available"
    BORROWED = "borrowed"
    RESERVED = "reserved"
    DAMAGED = "damaged"
    LOST = "lost"
    WITHDRAWN = "withdrawn"

class BorrowStatus(str, enum.Enum):
    """借阅状态枚举"""
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    LOST = "lost"

class ReservationStatus(str, enum.Enum):
    """预约状态枚举"""
    PENDING = "pending"
    READY = "ready"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class FineStatus(str, enum.Enum):
    """罚款状态枚举"""
    PENDING = "pending"
    PAID = "paid"
    WAIVED = "waived"

class FineType(str, enum.Enum):
    """罚款类型枚举"""
    OVERDUE = "overdue"
    DAMAGE = "damage"
    LOSS = "loss"

class PurchaseRequestStatus(str, enum.Enum):
    """荐购状态枚举"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PURCHASED = "purchased"

# 用户表
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20))
    role = Column(Enum(UserRole), default=UserRole.READER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    reader_card_number = Column(String(50), unique=True, index=True)  # 读者证号
    reader_type = Column(String(50))  # 读者类型：学生/教职工/社会读者
    max_borrow_count = Column(Integer, default=10)  # 最大借阅数量
    borrow_limit_days = Column(Integer, default=30)  # 借阅期限
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联
    borrow_records = relationship("BorrowRecord", back_populates="user", foreign_keys="BorrowRecord.user_id")
    reservations = relationship("Reservation", back_populates="user", foreign_keys="Reservation.user_id")
    fines = relationship("Fine", back_populates="user", foreign_keys="Fine.user_id")
    purchase_requests = relationship("PurchaseRequest", back_populates="user", foreign_keys="PurchaseRequest.user_id")
    operations_logs = relationship("SystemLog", back_populates="operator", foreign_keys="SystemLog.operator_id")

# 角色权限表
class Role(Base):
    __tablename__ = "roles"
    
    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(50), unique=True, nullable=False)
    permissions = Column(Text)  # JSON格式的权限列表
    description = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 图书分类表
class Category(Base):
    __tablename__ = "categories"
    
    category_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.category_id"))
    level = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    books = relationship("Book", back_populates="category")
    children = relationship("Category", back_populates="parent")
    parent = relationship("Category", back_populates="children", remote_side=[category_id])

# 图书主表
class Book(Base):
    __tablename__ = "books"
    
    book_id = Column(Integer, primary_key=True, index=True)
    isbn = Column(String(20), index=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100))
    publisher = Column(String(100))
    publish_year = Column(Integer)
    category_id = Column(Integer, ForeignKey("categories.category_id"))
    location = Column(String(100))  # 存放位置
    status = Column(Enum(BookStatus), default=BookStatus.AVAILABLE)
    total_copies = Column(Integer, default=1)
    available_copies = Column(Integer, default=1)
    price = Column(Float)
    cover_url = Column(String(500))
    description = Column(Text)
    call_number = Column(String(50), index=True)  # 索书号
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联
    category = relationship("Category", back_populates="books")
    copies = relationship("BookCopy", back_populates="book")
    reservations = relationship("Reservation", back_populates="book")

# 单册副本表
class BookCopy(Base):
    __tablename__ = "book_copies"
    
    copy_id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.book_id"), nullable=False)
    barcode = Column(String(50), unique=True, index=True, nullable=False)  # 条形码
    status = Column(Enum(CopyStatus), default=CopyStatus.AVAILABLE)
    location_detail = Column(String(100))  # 详细位置
    acquisition_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    book = relationship("Book", back_populates="copies")
    borrow_records = relationship("BorrowRecord", back_populates="copy")

# 借阅记录表
class BorrowRecord(Base):
    __tablename__ = "borrow_records"
    
    borrow_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    copy_id = Column(Integer, ForeignKey("book_copies.copy_id"), nullable=False)
    borrow_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=False)
    return_date = Column(DateTime(timezone=True))
    return_branch = Column(String(100))  # 归还分馆（支持异地还书）
    status = Column(Enum(BorrowStatus), default=BorrowStatus.ACTIVE)
    fine_amount = Column(Float, default=0)
    operator_id = Column(Integer, ForeignKey("users.user_id"))  # 操作员
    renew_count = Column(Integer, default=0)  # 续借次数
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    user = relationship("User", back_populates="borrow_records", foreign_keys=[user_id])
    copy = relationship("BookCopy", back_populates="borrow_records")
    operator = relationship("User", foreign_keys=[operator_id])
    fine = relationship("Fine", back_populates="borrow_record", uselist=False)

# 预约记录表
class Reservation(Base):
    __tablename__ = "reservations"
    
    reservation_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.book_id"), nullable=False)
    reservation_date = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(DateTime(timezone=True))
    status = Column(Enum(ReservationStatus), default=ReservationStatus.PENDING)
    queue_position = Column(Integer)  # 排队位置
    notification_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    user = relationship("User", back_populates="reservations")
    book = relationship("Book", back_populates="reservations")

# 罚款记录表
class Fine(Base):
    __tablename__ = "fines"
    
    fine_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    borrow_id = Column(Integer, ForeignKey("borrow_records.borrow_id"))
    fine_type = Column(Enum(FineType), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(FineStatus), default=FineStatus.PENDING)
    paid_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    user = relationship("User", back_populates="fines", foreign_keys=[user_id])
    borrow_record = relationship("BorrowRecord", back_populates="fine")

# 评论状态枚举
class CommentStatus(str, enum.Enum):
    PENDING = "pending"      # 待审核
    APPROVED = "approved"    # 已通过（公开）
    HIDDEN = "hidden"        # 已隐藏
    REJECTED = "rejected"    # 已拒绝

# 图书评分表
class BookRating(Base):
    __tablename__ = "book_ratings"

    rating_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.book_id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 星
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    user = relationship("User", foreign_keys=[user_id])
    book = relationship("Book", foreign_keys=[book_id])

# 图书评论表
class BookComment(Base):
    __tablename__ = "book_comments"

    comment_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.book_id"), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum(CommentStatus), default=CommentStatus.PENDING)
    admin_reply = Column(Text)  # 管理员回复
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    user = relationship("User", foreign_keys=[user_id])
    book = relationship("Book", foreign_keys=[book_id])

# 荐购申请表
class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"
    
    request_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    book_title = Column(String(200), nullable=False)
    author = Column(String(100))
    isbn = Column(String(20))
    reason = Column(Text)
    status = Column(Enum(PurchaseRequestStatus), default=PurchaseRequestStatus.PENDING)
    review_comment = Column(Text)
    reviewer_id = Column(Integer, ForeignKey("users.user_id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联
    user = relationship("User", back_populates="purchase_requests", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])

# 系统日志表（只增不改）
class SystemLog(Base):
    __tablename__ = "system_logs"
    
    log_id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("users.user_id"))
    operation_type = Column(String(50), nullable=False)  # 操作类型
    target_type = Column(String(50))  # 目标类型
    target_id = Column(Integer)  # 目标ID
    ip_address = Column(String(50))
    operation_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    details = Column(Text)  # 操作详情（JSON格式）
    before_data = Column(Text)  # 操作前数据快照
    after_data = Column(Text)  # 操作后数据快照
    
    # 关联
    operator = relationship("User", back_populates="operations_logs")

# 系统配置表
class SystemConfig(Base):
    __tablename__ = "system_configs"
    
    config_id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text)
    description = Column(String(200))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# 节假日表
class Holiday(Base):
    __tablename__ = "holidays"
    
    holiday_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    year = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 消息通知表
class Notification(Base):
    __tablename__ = "notifications"
    
    notification_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    type = Column(String(50))  # 消息类型
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    user = relationship("User")
