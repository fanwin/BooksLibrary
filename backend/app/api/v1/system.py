"""
系统配置、日志管理、用户管理和读者证路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
import csv
import io
from app.core.database import get_db
from app.models.models import (
    SystemLog, SystemConfig, User, Category, PurchaseRequest, Holiday, Notification,
    UserRole, UserStatus, PurchaseRequestStatus
)
from app.schemas.schemas import (
    SystemLogResponse, LogQuery, SystemConfigResponse,
    SystemConfigBase, CategoryCreate, CategoryUpdate, CategoryResponse,
    PurchaseRequestCreate, PurchaseRequestUpdate, PurchaseRequestResponse,
    UserUpdate, UserResponse, UserDetailResponse, AdminUserCreate,
    ReaderCardIssue, ReaderCardLoss, ReaderCardReplace,
)
from app.api.dependencies import (
    get_current_user, require_super_admin, require_auditor,
    require_admin, require_catalog_admin, require_circulation_admin
)
from app.core.security import get_password_hash, validate_password as validate_pwd_complexity
from app.core.audit_log import write_log
import json

router = APIRouter(tags=["系统管理"])

# ============ 系统日志（只增不改，审计员可查不可删） ============

@router.get("/logs", response_model=dict)
async def get_system_logs(
    operation_type: Optional[str] = None,
    operator_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    """查询系统审计日志 - 支持多维度筛选"""
    query = db.query(SystemLog)

    if operation_type:
        query = query.filter(SystemLog.operation_type == operation_type)
    if operator_id:
        query = query.filter(SystemLog.operator_id == operator_id)
    if start_date:
        query = query.filter(SystemLog.operation_time >= start_date)
    if end_date:
        query = query.filter(SystemLog.operation_time <= end_date)
    if keyword:
        query = query.filter(
            or_(
                SystemLog.operation_type.contains(keyword),
                SystemLog.target_type.contains(keyword),
                SystemLog.details.contains(keyword) if SystemLog.details.isnot(None) else False,
            )
        )

    total = query.count()
    logs = query.order_by(SystemLog.operation_time.desc()).offset((page - 1) * size).limit(size).all()

    items = []
    for log in logs:
        item = SystemLogResponse.model_validate(log.__dict__).model_dump()
        # 尝试解析 details JSON
        try:
            item["details_parsed"] = json.loads(log.details) if log.details else None
        except (json.JSONDecodeError, TypeError):
            item["details_parsed"] = log.details
        items.append(item)

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


@router.get("/logs/export")
async def export_logs(
    operation_type: Optional[str] = None,
    operator_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    """导出审计日志为 CSV 格式"""
    from fastapi.responses import StreamingResponse

    query = db.query(SystemLog)
    if operation_type:
        query = query.filter(SystemLog.operation_type == operation_type)
    if operator_id:
        query = query.filter(SystemLog.operator_id == operator_id)
    if start_date:
        query = query.filter(SystemLog.operation_time >= start_date)
    if end_date:
        query = query.filter(SystemLog.operation_time <= end_date)

    logs = query.order_by(SystemLog.operation_time.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "日志ID", "操作人ID", "操作类型", "目标类型", "目标ID",
        "IP地址", "操作时间", "操作详情", "变更前数据", "变更后数据"
    ])

    for log in logs:
        writer.writerow([
            log.log_id,
            log.operator_id or "",
            log.operation_type,
            log.target_type or "",
            log.target_id or "",
            log.ip_address or "",
            log.operation_time.strftime("%Y-%m-%d %H:%M:%S") if log.operation_time else "",
            log.details or "",
            log.before_data or "",
            log.after_data or "",
        ])

    output.seek(0)
    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # 记录导出日志
    write_log(db, current_user.user_id, "log:export", None, None,
              details={"filter_count": len(logs), "filters": {"operation_type": operation_type}})
    db.commit()

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ 系统配置 ============

@router.get("/configs", response_model=dict)
async def get_system_configs(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    configs = db.query(SystemConfig).all()
    return {
        "code": 200,
        "message": "success",
        "data": [SystemConfigResponse.model_validate(c.__dict__) for c in configs]
    }


@router.post("/configs", response_model=SystemConfigResponse)
async def create_system_config(
    config_data: SystemConfigBase,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(SystemConfig).filter(
        SystemConfig.config_key == config_data.config_key
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="配置项已存在")

    config = SystemConfig(
        config_key=config_data.config_key,
        config_value=config_data.config_value,
        description=config_data.description
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    write_log(db, current_user.user_id, "config:create", "SystemConfig", config.config_id,
              details={"key": config.config_key})
    db.commit()

    return config


@router.put("/configs/{config_key}", response_model=SystemConfigResponse)
async def update_system_config(
    config_key: str,
    config_value: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")

    old_value = config.config_value
    config.config_value = config_value
    db.commit()
    db.refresh(config)

    write_log(db, current_user.user_id, "config:update", "SystemConfig", config.config_id,
              before_data={"config_key": config_key, "old_value": old_value},
              after_data={"config_key": config_key, "new_value": config_value})
    db.commit()

    return config


# ============ 分类管理（保持原有逻辑 + 审计） ============

@router.get("/categories", response_model=dict)
async def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    categories = db.query(Category).order_by(Category.sort_order).all()

    def build_tree(cats, parent_id=None):
        tree = []
        for cat in cats:
            if cat.parent_id == parent_id:
                node = CategoryResponse.model_validate(cat.__dict__)
                node.children = build_tree(cats, cat.category_id)
                tree.append(node)
        return tree

    tree = build_tree(categories)
    return {"code": 200, "message": "success", "data": tree}


@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    level = 1
    if category_data.parent_id:
        parent = db.query(Category).filter(Category.category_id == category_data.parent_id).first()
        if parent:
            level = parent.level + 1
    category = Category(
        name=category_data.name, parent_id=category_data.parent_id,
        level=level, sort_order=category_data.sort_order
    )
    db.add(category)
    db.commit()
    db.refresh(category)

    write_log(db, current_user.user_id, "category:create", "Category", category.category_id,
              details={"name": category_data.name})
    db.commit()
    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    update_data = category_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)

    write_log(db, current_user.user_id, "category:update", "Category", category_id,
              details=update_data)
    db.commit()
    return category


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    children = db.query(Category).filter(Category.parent_id == category_id).first()
    if children:
        raise HTTPException(status_code=400, detail="该分类下有子分类，无法删除")
    from app.models.models import Book
    books = db.query(Book).filter(Book.category_id == category_id).first()
    if books:
        raise HTTPException(status_code=400, detail="该分类下有图书，无法删除")

    before = {"name": category.name, "id": category.category_id}
    db.delete(category)
    write_log(db, current_user.user_id, "category:delete", "Category", category_id,
              before_data=before)
    db.commit()
    return {"code": 200, "message": "分类已删除"}


# ============ 荐购管理（保持原有逻辑） ============

@router.get("/purchase-requests", response_model=dict)
async def get_purchase_requests(
    status_filter: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(PurchaseRequest)
    if current_user.role.value == UserRole.READER.value:
        query = query.filter(PurchaseRequest.user_id == current_user.user_id)
    if status_filter:
        query = query.filter(PurchaseRequest.status == status_filter)
    total = query.count()
    requests = query.order_by(PurchaseRequest.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "code": 200, "message": "success",
        "data": {
            "items": [PurchaseRequestResponse.model_validate(r.__dict__) for r in requests],
            "total": total, "page": page, "size": size
        }
    }


@router.post("/purchase-requests", response_model=PurchaseRequestResponse)
async def create_purchase_request(
    request_data: PurchaseRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    request = PurchaseRequest(
        user_id=current_user.user_id, book_title=request_data.book_title,
        author=request_data.author, isbn=request_data.isbn, reason=request_data.reason,
        status=PurchaseRequestStatus.PENDING
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.put("/purchase-requests/{request_id}", response_model=PurchaseRequestResponse)
async def review_purchase_request(
    request_id: int,
    review_data: PurchaseRequestUpdate,
    current_user: User = Depends(require_catalog_admin),
    db: Session = Depends(get_db)
):
    request = db.query(PurchaseRequest).filter(PurchaseRequest.request_id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="荐购申请不存在")
    if request.status != PurchaseRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="该申请已审核")

    old_status = request.status.value
    request.status = review_data.status
    request.review_comment = review_data.review_comment
    request.reviewer_id = current_user.user_id
    db.commit()
    db.refresh(request)

    write_log(db, current_user.user_id, "purchase:review", "PurchaseRequest", request_id,
              before_data={"old_status": old_status},
              after_data={"new_status": review_data.status, "comment": review_data.review_comment},
              details={"book_title": request.book_title})
    db.commit()
    return request


# ==================== 用户管理（增强版 CRUD + 审计）====================

def _get_reader_type_defaults(reader_type: str) -> dict:
    """根据读者类型返回默认借阅参数"""
    defaults = {
        "student":   {"max_borrow_count": 10, "borrow_limit_days": 30},
        "staff":     {"max_borrow_count": 15, "borrow_limit_days": 45},
        "public":    {"max_borrow_count": 5,  "borrow_limit_days": 14},
        "admin":     {"max_borrow_count": 20, "borrow_limit_days": 60},
    }
    return defaults.get(reader_type, defaults["student"])


def _generate_card_number(user_id: int, reader_type: str) -> str:
    """生成唯一读者证号：RD + 年份(2位) + 类型码 + 序号(4位补零)"""
    type_map = {"student": "S", "staff": "T", "public": "P", "admin": "A"}
    type_code = type_map.get(reader_type.upper(), "X")
    year_suffix = datetime.now().strftime("%y")
    return f"RD{year_suffix}{type_code}{user_id:04d}"


@router.post("/users", response_model=UserDetailResponse)
async def create_user(
    user_data: AdminUserCreate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """管理员创建用户"""
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已被注册")

    if not validate_pwd_complexity(user_data.password):
        raise HTTPException(status_code=400, detail="密码必须包含大小写字母、数字和特殊字符，且长度至少8位")

    # 根据读者类型设置借阅参数
    borrow_defaults = _get_reader_type_defaults(user_data.reader_type)

    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        email=user_data.email,
        phone=user_data.phone,
        role=UserRole(user_data.role) if user_data.role else UserRole.READER,
        status=UserStatus(user_data.status) if user_data.status else UserStatus.ACTIVE,
        reader_type=user_data.reader_type,
        max_borrow_count=borrow_defaults["max_borrow_count"],
        borrow_limit_days=borrow_defaults["borrow_limit_days"],
    )

    db.add(new_user)
    db.flush()  # 获取 user_id 但暂不提交

    # 自动生成读者证号
    new_user.reader_card_number = _generate_card_number(new_user.user_id, user_data.reader_type)

    db.commit()
    db.refresh(new_user)

    write_log(db, current_user.user_id, "user:create", "User", new_user.user_id,
              after_data={
                  "username": new_user.username, "role": new_user.role.value,
                  "reader_type": new_user.reader_type, "card_no": new_user.reader_card_number
              })
    db.commit()

    return new_user


@router.get("/users", response_model=dict)
async def get_users(
    role: Optional[str] = None,
    status_filter: Optional[str] = None,
    keyword: Optional[str] = Query(None, description="搜索用户名/邮箱/手机号/证号"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """查询用户列表（支持搜索、角色/状态筛选）"""
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)
    if status_filter:
        query = query.filter(User.status == status_filter)
    if keyword:
        query = query.filter(
            or_(
                User.username.contains(keyword),
                User.email.contains(keyword),
                User.phone.contains(keyword),
                User.reader_card_number.contains(keyword),
            )
        )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size).all()

    items = []
    for u in users:
        d = u.__dict__.copy()
        # 清除 SQLAlchemy 内部属性
        d = {k: v for k, v in d.items() if not k.startswith('_sa_')}
        # 格式化时间
        if d.get('created_at'):
            d['created_at'] = d['created_at'].isoformat() if hasattr(d['created_at'], 'isoformat') else str(d['created_at'])
        items.append(d)

    return {
        "code": 200, "message": "success",
        "data": {
            "items": items, "total": total,
            "page": page, "size": size,
            "pages": (total + size - 1) // size
        }
    }


@router.get("/users/{user_id}", response_model=dict)
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取用户详情"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 统计借阅信息
    from app.models.models import BorrowRecord, BorrowStatus, Fine, FineStatus

    active_borrows = db.query(BorrowRecord).filter(
        and_(BorrowRecord.user_id == user_id, BorrowRecord.status == BorrowStatus.ACTIVE)
    ).count()

    total_borrows = db.query(BorrowRecord).filter(BorrowRecord.user_id == user_id).count()

    unpaid_fines = db.query(Fine).filter(
        and_(Fine.user_id == user_id, Fine.status == FineStatus.PENDING)
    ).with_entities(func.sum(Fine.amount)).scalar() or 0

    return {
        "code": 200, "message": "success",
        "data": {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "role": user.role.value,
            "status": user.status.value,
            "reader_card_number": user.reader_card_number,
            "reader_type": user.reader_type,
            "max_borrow_count": user.max_borrow_count,
            "borrow_limit_days": user.borrow_limit_days,
            "active_borrows": active_borrows,
            "total_borrows": total_borrows,
            "unpaid_fines": round(unpaid_fines, 2),
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
    }


@router.put("/users/{user_id}", response_model=dict)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """更新用户信息（含审计快照）"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 记录修改前快照
    before_snapshot = {
        "username": user.username, "email": user.email, "phone": user.phone,
        "role": user.role.value, "status": user.status.value, "reader_type": user.reader_type,
    }

    update_data = user_data.model_dump(exclude_unset=True)
    # 如果修改了 reader_type，同步更新借阅参数
    if "reader_type" in update_data and update_data["reader_type"]:
        defaults = _get_reader_type_defaults(update_data["reader_type"])
        user.max_borrow_count = defaults["max_borrow_count"]
        user.borrow_limit_days = defaults["borrow_limit_days"]

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    after_snapshot = {**before_snapshot}
    after_snapshot.update(update_data)

    write_log(db, current_user.user_id, "user:update", "User", user_id,
              before_data=before_snapshot, after_data=after_snapshot,
              details={"operator": current_user.username, "target_user": user.username})
    db.commit()

    return {"code": 200, "message": "用户信息已更新", "data": UserDetailResponse.model_validate(user).model_dump()}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """删除用户（软删除标记+审计记录）"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 不允许删除自己
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="不能删除自己的账户")

    # 检查是否有未归还的图书
    from app.models.models import BorrowRecord, BorrowStatus
    active_count = db.query(BorrowRecord).filter(
        and_(BorrowRecord.user_id == user_id, BorrowRecord.status == BorrowStatus.ACTIVE)
    ).count()
    if active_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该用户仍有 {active_count} 本图书未归还，请先处理后再删除"
        )

    before_snapshot = {
        "username": user.username, "email": user.email,
        "role": user.role.value, "status": user.status.value,
        "reader_card_number": user.reader_card_number,
    }

    db.delete(user)

    write_log(db, current_user.user_id, "user:delete", "User", user_id,
              before_data=before_snapshot,
              details={"deleted_username": user.username})
    db.commit()

    return {"code": 200, "message": f"用户 '{user.username}' 已被删除"}


@router.post("/users/{user_id}/suspend", response_model=dict)
async def suspend_user(
    user_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """禁用/挂失用户"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    old_status = user.status.value
    user.status = UserStatus.SUSPENDED
    db.commit()

    write_log(db, current_user.user_id, "user:suspend", "User", user_id,
              before_data={"username": user.username, "old_status": old_status},
              after_data={"new_status": "suspended"},
              details={"reason": "管理员手动禁用"})
    db.commit()

    return {"code": 200, "message": f"用户 '{user.username}' 已被禁用"}


@router.post("/users/{user_id}/activate", response_model=dict)
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """激活用户"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    old_status = user.status.value
    user.status = UserStatus.ACTIVE
    db.commit()

    write_log(db, current_user.user_id, "user:activate", "User", user_id,
              before_data={"username": user.username, "old_status": old_status},
              after_data={"new_status": "active"})
    db.commit()

    return {"code": 200, "message": f"用户 '{user.username}' 已激活"}


# ==================== 读者证管理 ====================

@router.post("/users/{user_id}/reader-card/issue", response_model=dict)
async def issue_reader_card(
    user_id: int,
    card_data: ReaderCardIssue,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """为用户办理/重新办理读者证"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.status.value != "active":
        raise HTTPException(status_code=400, detail="用户状态不正常，无法办证")

    # 如果已有证号且未挂失，不允许重复办证
    if user.reader_card_number and user.status.value != "suspended":
        raise HTTPException(status_code=400, detail=f"该用户已有证号：{user.reader_card_number}，如需换证请先挂失")

    old_card = user.reader_card_number
    new_card_number = _generate_card_number(user.user_id, card_data.reader_type)

    user.reader_card_number = new_card_number
    user.reader_type = card_data.reader_type
    # 同步借阅参数
    defaults = _get_reader_type_defaults(card_data.reader_type)
    user.max_borrow_count = defaults["max_borrow_count"]
    user.borrow_limit_days = defaults["borrow_limit_days"]
    # 办新证时自动激活（如果是挂失后补办）
    user.status = UserStatus.ACTIVE

    db.commit()
    db.refresh(user)

    write_log(db, current_user.user_id, "reader_card:issue", "ReaderCard", user_id,
              before_data={"old_card": old_card},
              after_data={"new_card": new_card_number, "reader_type": card_data.reader_type},
              details={"username": user.username})
    db.commit()

    return {
        "code": 200,
        "message": "读者证办理成功",
        "data": {"card_number": new_card_number, "reader_type": card_data.reader_type}
    }


@router.post("/users/{user_id}/reader-card/loss", response_model=dict)
async def report_loss_reader_card(
    user_id: int,
    loss_data: ReaderCardLoss,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """读者证挂失"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not user.reader_card_number:
        raise HTTPException(status_code=400, detail="该用户没有读者证")

    old_status = user.status.value
    old_card = user.reader_card_number

    # 挂失后设为 suspended 状态
    user.status = UserStatus.SUSPENDED

    db.commit()
    db.refresh(user)

    write_log(db, current_user.user_id, "reader_card:loss", "ReaderCard", user_id,
              before_data={
                  "card_number": old_card,
                  "old_status": old_status,
              },
              after_data={"new_status": "suspended"},
              details={
                  "username": user.username,
                  "reason": loss_data.reason,
                  "operator": current_user.username,
              })
    db.commit()

    return {"code": 200, "message": f"读者证 {old_card} 已挂失，用户借阅功能暂停"}


@router.post("/users/{user_id}/reader-card/replace", response_model=dict)
async def replace_reader_card(
    user_id: int,
    replace_data: ReaderCardReplace,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """读者证补换（挂失后重新发证）"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not user.reader_card_number:
        raise HTTPException(status_code=400, detail="该用户没有读者证，请先办证")

    old_card = user.reader_card_number
    new_type = replace_data.reader_type or user.reader_type
    new_card = _generate_card_number(user.user_id, new_type) + "R"  # 补证加 R 后缀标识

    user.reader_card_number = new_card
    user.reader_type = new_type
    user.status = UserStatus.ACTIVE  # 补证后自动恢复为正常

    # 更新借阅参数
    defaults = _get_reader_type_defaults(new_type)
    user.max_borrow_count = defaults["max_borrow_count"]
    user.borrow_limit_days = defaults["borrow_limit_days"]

    db.commit()
    db.refresh(user)

    write_log(db, current_user.user_id, "reader_card:replace", "ReaderCard", user_id,
              before_data={"old_card": old_card},
              after_data={"new_card": new_card, "reader_type": new_type},
              details={"username": user.username})
    db.commit()

    return {
        "code": 200,
        "message": f"读者证补换成功（原证：{old_card}）",
        "data": {"card_number": new_card, "reader_type": new_type}
    }


@router.get("/users/{user_id}/reader-card", response_model=dict)
async def get_reader_card_info(
    user_id: int,
    current_user: User = Depends(require_circulation_admin),
    db: Session = Depends(get_db)
):
    """查看用户读者证详情"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    from app.models.models import BorrowRecord, BorrowStatus

    active_borrows = db.query(BorrowRecord).filter(
        and_(BorrowRecord.user_id == user_id, BorrowRecord.status == BorrowStatus.ACTIVE)
    ).count()

    return {
        "code": 200, "message": "success",
        "data": {
            "user_id": user.user_id,
            "username": user.username,
            "card_number": user.reader_card_number,
            "reader_type": user.reader_type,
            "status": user.status.value,
            "max_borrow_count": user.max_borrow_count,
            "borrow_limit_days": user.borrow_limit_days,
            "current_active_borrows": active_borrows,
            "remaining_quota": max(0, (user.max_borrow_count or 0) - active_borrows),
        }
    }


# ============ 节假日管理 ============

class HolidayCreate(BaseModel):
    name: str = Field(..., max_length=100)
    date: str  # YYYY-MM-DD format
    year: Optional[int] = None

class HolidayUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None


@router.get("/holidays", response_model=dict)
async def get_holidays(
    year: Optional[int] = Query(None, description="筛选年份"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取节假日列表"""
    query = db.query(Holiday)
    if year:
        query = query.filter(Holiday.year == year)
    holidays = query.order_by(Holiday.date).all()
    return {
        "code": 200,
        "message": "success",
        "data": [
            {
                "holiday_id": h.holiday_id,
                "name": h.name,
                "date": h.date.isoformat() if h.date else None,
                "year": h.year,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in holidays
        ]
    }


@router.post("/holidays", response_model=dict)
async def create_holiday(
    holiday_data: HolidayCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """创建节假日"""
    from dateutil import parser as date_parser
    try:
        holiday_date = date_parser.parse(holiday_data.date).date()
    except Exception:
        raise HTTPException(status_code=400, detail="日期格式无效，请使用 YYYY-MM-DD")

    year = holiday_data.year or holiday_date.year

    # 检查是否已存在同一天的节假日
    existing = db.query(Holiday).filter(
        Holiday.date == holiday_date
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"{holiday_date} 已存在节假日「{existing.name}」")

    holiday = Holiday(
        name=holiday_data.name,
        date=holiday_date,
        year=year,
    )
    db.add(holiday)
    db.commit()
    db.refresh(holiday)

    write_log(db, current_user.user_id, "holiday:create", "Holiday", holiday.holiday_id,
              details={"name": holiday_data.name, "date": str(holiday_date)})
    db.commit()

    return {"code": 200, "message": "节假日创建成功", "data": {"holiday_id": holiday.holiday_id}}


@router.put("/holidays/{holiday_id}", response_model=dict)
async def update_holiday(
    holiday_id: int,
    holiday_data: HolidayUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """更新节假日"""
    holiday = db.query(Holiday).filter(Holiday.holiday_id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="节假日不存在")

    if holiday_data.name:
        holiday.name = holiday_data.name
    if holiday_data.date:
        from dateutil import parser as date_parser
        try:
            new_date = date_parser.parse(holiday_data.date).date()
            holiday.date = new_date
            holiday.year = new_date.year
        except Exception:
            raise HTTPException(status_code=400, detail="日期格式无效")

    db.commit()
    db.refresh(holiday)

    write_log(db, current_user.user_id, "holiday:update", "Holiday", holiday_id,
              details={"name": holiday.name})
    db.commit()

    return {"code": 200, "message": "节假日已更新"}


@router.delete("/holidays/{holiday_id}", response_model=dict)
async def delete_holiday(
    holiday_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """删除节假日"""
    holiday = db.query(Holiday).filter(Holiday.holiday_id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="节假日不存在")

    before = {"name": holiday.name, "date": str(holiday.date)}
    db.delete(holiday)
    write_log(db, current_user.user_id, "holiday:delete", "Holiday", holiday_id,
              before_data=before)
    db.commit()

    return {"code": 200, "message": "节假日已删除"}


@router.post("/holidays/batch", response_model=dict)
async def batch_create_holidays(
    holidays_data: list[HolidayCreate],
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """批量导入节假日"""
    from dateutil import parser as date_parser
    created = 0
    skipped = 0
    for hd in holidays_data:
        try:
            holiday_date = date_parser.parse(hd.date).date()
        except Exception:
            skipped += 1
            continue

        existing = db.query(Holiday).filter(Holiday.date == holiday_date).first()
        if existing:
            skipped += 1
            continue

        year = hd.year or holiday_date.year
        holiday = Holiday(name=hd.name, date=holiday_date, year=year)
        db.add(holiday)
        created += 1

    db.commit()
    write_log(db, current_user.user_id, "holiday:create", "Holiday", 0,
              details={"batch_create": created, "skipped": skipped})
    db.commit()

    return {
        "code": 200,
        "message": f"批量导入完成：成功 {created} 条，跳过 {skipped} 条",
        "data": {"created": created, "skipped": skipped}
    }


# ============ 通知系统 ============

class NotificationCreate(BaseModel):
    user_id: int
    title: str = Field(..., max_length=200)
    content: Optional[str] = None
    type: Optional[str] = "system"


@router.get("/notifications", response_model=dict)
async def get_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_read: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的通知列表"""
    query = db.query(Notification).filter(Notification.user_id == current_user.user_id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    total = query.count()
    notifications = query.order_by(Notification.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [
                {
                    "notification_id": n.notification_id,
                    "title": n.title,
                    "content": n.content,
                    "type": n.type,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifications
            ],
            "total": total,
            "unread_count": db.query(Notification).filter(
                and_(Notification.user_id == current_user.user_id, Notification.is_read == False)
            ).count()
        }
    }


@router.get("/notifications/unread-count", response_model=dict)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取未读通知数量"""
    count = db.query(Notification).filter(
        and_(Notification.user_id == current_user.user_id, Notification.is_read == False)
    ).count()
    return {"code": 200, "data": {"count": count}}


@router.put("/notifications/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记通知为已读"""
    notification = db.query(Notification).filter(
        and_(Notification.notification_id == notification_id, Notification.user_id == current_user.user_id)
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")
    notification.is_read = True
    db.commit()
    return {"code": 200, "message": "已标记为已读"}


@router.put("/notifications/read-all", response_model=dict)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记所有通知为已读"""
    db.query(Notification).filter(
        and_(Notification.user_id == current_user.user_id, Notification.is_read == False)
    ).update({"is_read": True})
    db.commit()
    return {"code": 200, "message": "已全部标记为已读"}


@router.delete("/notifications/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除通知"""
    notification = db.query(Notification).filter(
        and_(Notification.notification_id == notification_id, Notification.user_id == current_user.user_id)
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")
    db.delete(notification)
    db.commit()
    return {"code": 200, "message": "通知已删除"}


@router.post("/notifications", response_model=dict)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员发送通知（支持群发）"""
    user = db.query(User).filter(User.user_id == notification_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    notification = Notification(
        user_id=notification_data.user_id,
        title=notification_data.title,
        content=notification_data.content,
        type=notification_data.type or "system",
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    return {"code": 200, "message": "通知已发送", "data": {"notification_id": notification.notification_id}}
