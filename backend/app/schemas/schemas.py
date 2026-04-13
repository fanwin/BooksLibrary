"""
Pydantic数据验证模式
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime, timezone

# ============ 通用响应模式 ============
class ResponseModel(BaseModel):
    """统一响应格式"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PaginationResponse(BaseModel):
    """分页响应"""
    items: list
    total: int
    page: int
    size: int
    pages: int

# ============ 用户相关模式 ============
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: Optional[str] = "reader"
    reader_type: Optional[str] = "student"

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    reader_type: Optional[str] = None

class UserResponse(UserBase):
    user_id: int
    role: str
    status: str
    reader_card_number: Optional[str] = None
    reader_type: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str
    captcha_key: Optional[str] = Field(default=None, alias="captchaKey")
    captcha_code: Optional[str] = Field(default=None, alias="captchaCode")

    model_config = {"populate_by_name": True}

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # 会话生命周期信息（前端用于超时检测和倒计时提示）
    expires_in: int = 3600          # Token 有效期（秒），默认 1 小时
    session_expires_at: Optional[str] = None   # 会话到期时间 ISO 格式

# ============ 图书相关模式 ============
class BookBase(BaseModel):
    isbn: Optional[str] = None
    title: str = Field(..., max_length=200)
    author: Optional[str] = None
    publisher: Optional[str] = None
    publish_year: Optional[int] = None
    category_id: Optional[int] = None
    location: Optional[str] = None
    price: Optional[float] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    call_number: Optional[str] = None

class BookCreate(BookBase):
    total_copies: int = 1

class BookUpdate(BaseModel):
    isbn: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    publish_year: Optional[int] = None
    category_id: Optional[int] = None
    location: Optional[str] = None
    status: Optional[str] = None
    price: Optional[float] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    call_number: Optional[str] = None

class BookResponse(BookBase):
    book_id: int
    status: str
    total_copies: int
    available_copies: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class BookSearch(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    category_id: Optional[int] = None
    status: Optional[str] = None
    page: int = 1
    size: int = 20

# ============ 单册副本模式 ============
class BookCopyBase(BaseModel):
    book_id: int
    barcode: str
    location_detail: Optional[str] = None

class BookCopyCreate(BookCopyBase):
    pass

class BookCopyResponse(BookCopyBase):
    copy_id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ 借阅相关模式 ============
class BorrowCreate(BaseModel):
    user_id: int
    copy_id: int

class BorrowResponse(BaseModel):
    borrow_id: int
    user_id: int
    copy_id: int
    borrow_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    status: str
    fine_amount: float
    renew_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BorrowReturn(BaseModel):
    operator_id: Optional[int] = None
    return_branch: Optional[str] = None  # 归还分馆（异地还书）

class BorrowRenew(BaseModel):
    operator_id: Optional[int] = None

# ============ 预约相关模式 ============
class ReservationCreate(BaseModel):
    user_id: int
    book_id: int

class ReservationResponse(BaseModel):
    reservation_id: int
    user_id: int
    book_id: int
    reservation_date: datetime
    expiry_date: Optional[datetime] = None
    status: str
    queue_position: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ 罚款相关模式 ============
class FineResponse(BaseModel):
    fine_id: int
    user_id: int
    borrow_id: Optional[int] = None
    fine_type: str
    amount: float
    status: str
    paid_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class FinePay(BaseModel):
    amount: float

# ============ 图书评分与评论模式 ============
class BookRatingCreate(BaseModel):
    book_id: int
    rating: int = Field(..., ge=1, le=5)

class BookRatingResponse(BaseModel):
    rating_id: int
    user_id: int
    book_id: int
    rating: int
    created_at: datetime

    class Config:
        from_attributes = True

class BookCommentCreate(BaseModel):
    book_id: int
    content: str = Field(..., min_length=2, max_length=1000)

class BookCommentUpdate(BaseModel):
    status: Optional[str] = None  # approved/hidden/rejected
    admin_reply: Optional[str] = None

class BookCommentResponse(BaseModel):
    comment_id: int
    user_id: int
    username: Optional[str] = None
    book_id: int
    content: str
    status: str
    admin_reply: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ============ 荐购相关模式 ============
class PurchaseRequestCreate(BaseModel):
    book_title: str = Field(..., max_length=200)
    author: Optional[str] = None
    isbn: Optional[str] = None
    reason: Optional[str] = None

class PurchaseRequestUpdate(BaseModel):
    status: str
    review_comment: Optional[str] = None

class PurchaseRequestResponse(BaseModel):
    request_id: int
    user_id: int
    book_title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    reason: Optional[str] = None
    status: str
    review_comment: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ============ 系统日志模式 ============
class SystemLogResponse(BaseModel):
    log_id: int
    operator_id: Optional[int] = None
    operation_type: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    ip_address: Optional[str] = None
    operation_time: datetime
    details: Optional[str] = None
    
    class Config:
        from_attributes = True

class LogQuery(BaseModel):
    operation_type: Optional[str] = None
    operator_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    size: int = 20

# ============ 分类模式 ============
class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    parent_id: Optional[int] = None
    sort_order: int = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None

class CategoryResponse(CategoryBase):
    category_id: int
    level: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ 系统配置模式 ============
class SystemConfigBase(BaseModel):
    config_key: str = Field(..., max_length=100)
    config_value: str
    description: Optional[str] = None

class SystemConfigResponse(SystemConfigBase):
    config_id: int
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ============ 统计模式 ============
class BorrowTrendData(BaseModel):
    date: str
    count: int

class HotBookData(BaseModel):
    book_id: int
    title: str
    author: str
    borrow_count: int

class CategoryStatData(BaseModel):
    category_name: str
    book_count: int
    borrow_count: int

class DashboardStats(BaseModel):
    today_borrows: int
    today_returns: int
    today_fines: float
    total_borrowed: int
    total_overdue: int
    total_reservations: int
    total_books: int
    total_readers: int

# ============ 密码相关模式 ============
class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

class PasswordReset(BaseModel):
    email: EmailStr
    new_password: str = Field(..., min_length=8)

class AdminPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)

# ============ 用户详情模式（含借阅参数） ============
class UserDetailResponse(UserResponse):
    max_borrow_count: Optional[int] = None
    borrow_limit_days: Optional[int] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True

class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str = Field(..., min_length=8)
    role: str = "reader"
    status: str = "active"
    reader_type: str = "student"

class UserListQuery(BaseModel):
    role: Optional[str] = None
    status_filter: Optional[str] = None
    keyword: Optional[str] = None
    page: int = 1
    size: int = 20

# ============ 角色权限模式 ============
class RoleCreate(BaseModel):
    role_name: str = Field(..., min_length=1, max_length=50)
    permissions: Optional[List[str]] = []
    description: Optional[str] = None

class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    permissions: Optional[List[str]] = None
    description: Optional[str] = None

class RoleResponse(BaseModel):
    role_id: int
    role_name: str
    permissions: Optional[str] = None  # JSON string from DB
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ============ 读者证模式 ============
class ReaderCardIssue(BaseModel):
    user_id: int
    reader_type: str = "student"  # student/staff/public

class ReaderCardLoss(BaseModel):
    reason: Optional[str] = None

class ReaderCardReplace(BaseModel):
    reader_type: Optional[str] = None

# ============ 验证码相关模式 ============
class CaptchaResponse(BaseModel):
    captcha_key: str
    captcha_image: str          # Base64 编码的 PNG 图片
    expire_in: int              # 有效期（秒）

class CaptchaVerify(BaseModel):
    captcha_key: str
    captcha_code: str


# ============ 权限常量 ============
ALL_PERMISSIONS = [
    # 运营看板
    "dashboard:read",
    # 图书管理
    "book:create", "book:read", "book:update", "book:delete",
    # 借阅管理
    "borrow:create", "borrow:read", "borrow:return", "borrow:renew", "borrow:approve",
    # 用户管理
    "user:create", "user:read", "user:update", "user:delete", "user:suspend",
    # 角色权限管理
    "role:create", "role:read", "role:update", "role:delete",
    # 系统配置
    "config:read", "config:update",
    # 日志审计
    "log:read", "log:export",
    # 分类管理
    "category:create", "category:read", "category:update", "category:delete",
    # 预约管理
    "reservation:create", "reservation:read", "reservation:update", "reservation:cancel",
    # 罚款管理
    "fine:read", "fine:update",
    # 荐购管理
    "purchase:read", "purchase:review",
    # 读者证管理
    "reader_card:issue", "reader_card:loss", "reader_card:replace", "reader_card:read",
    # 统计分析
    "statistics:read", "statistics:export",
]

# 默认角色权限映射
DEFAULT_ROLE_PERMISSIONS = {
    "super_admin": ALL_PERMISSIONS,
    "catalog_admin": [
        "dashboard:read",
        "book:create", "book:read", "book:update", "book:delete",
        "ebook:create", "ebook:read", "ebook:update", "ebook:delete",
        "category:create", "category:read", "category:update", "category:delete",
        "config:read", "log:read",
        "purchase:read", "purchase:review",
        "statistics:read",
    ],
    "circulation_admin": [
        "dashboard:read",
        "borrow:create", "borrow:read", "borrow:return", "borrow:renew", "borrow:approve",
        "ebook:read", "ebook:borrow", "ebook:return",
        "user:read", "reservation:create", "reservation:read", "reservation:update", "reservation:cancel",
        "fine:read", "fine:update", "log:read",
        "reader_card:issue", "reader_card:loss", "reader_card:replace", "reader_card:read",
        "statistics:read",
    ],
    "reader": [
        "book:read", "category:read",
        "ebook:read", "ebook:borrow", "ebook:return",
        "borrow:read", "reservation:create", "reservation:read", "reservation:cancel",
    ],
    "auditor": [
        "dashboard:read",
        "log:read", "log:export",
        "user:read", "borrow:read", "fine:read",
        "ebook:read",
        "config:read",
        "statistics:read", "statistics:export",
    ],
}

# ============ 电子书相关模式 ============
class EBookBase(BaseModel):
    """电子书基础模型"""
    isbn: Optional[str] = None
    title: str = Field(..., max_length=200)
    author: Optional[str] = None
    publisher: Optional[str] = None
    publish_year: Optional[int] = None
    category_id: Optional[int] = None
    file_format: str
    file_size: Optional[int] = None
    file_path: str
    cover_url: Optional[str] = None
    description: Optional[str] = None
    call_number: Optional[str] = None

class EBookCreate(EBookBase):
    """电子书创建模型"""
    total_copies: int = 1

class EBookUpdate(BaseModel):
    """电子书更新模型"""
    isbn: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    publish_year: Optional[int] = None
    category_id: Optional[int] = None
    file_format: Optional[str] = None
    file_size: Optional[int] = None
    file_path: Optional[str] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    call_number: Optional[str] = None
    total_copies: Optional[int] = None

class EBookResponse(EBookBase):
    """电子书响应模型"""
    ebook_id: int
    total_copies: int
    available_copies: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class EBookBorrowResponse(BaseModel):
    """电子书借阅响应模型"""
    borrow_id: int
    ebook_id: int
    title: str
    author: Optional[str] = None
    file_format: str
    borrow_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    status: str
    
    class Config:
        from_attributes = True
