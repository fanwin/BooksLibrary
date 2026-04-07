"""
认证路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token, validate_password
from app.models.models import User, UserRole, UserStatus
from app.schemas.schemas import (
    UserCreate, UserLogin, TokenResponse,
    UserResponse, PasswordChange, PasswordReset, AdminPasswordReset
)
from app.api.dependencies import get_current_user, require_super_admin, get_user_permissions

router = APIRouter(prefix="/auth", tags=["认证"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册")
    
    if not validate_password(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码必须包含大小写字母、数字和特殊字符，且长度至少8位"
        )
    
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        email=user_data.email,
        phone=user_data.phone,
        role=UserRole.READER,  # 注册接口固定为普通读者，防止权限提升
        status=UserStatus.ACTIVE,
        reader_type=user_data.reader_type if user_data.reader_type else "student"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 写入审计日志
    from app.core.audit_log import write_log
    write_log(db, new_user.user_id, "user:create", "User", new_user.user_id,
              details={"username": new_user.username, "role": new_user.role.value})
    db.commit()
    
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录（支持用户名或邮箱）"""
    # 支持用户名或邮箱登录
    user = db.query(User).filter(
        (User.username == login_data.username) | (User.email == login_data.username)
    ).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"用户账户状态：{user.status.value}"
        )
    
    access_token = create_access_token(data={"sub": user.user_id})
    refresh_token = create_refresh_token(data={"sub": user.user_id})
    
    # 记录登录日志
    from app.core.audit_log import write_log
    write_log(db, user.user_id, "user:login", "User", user.user_id,
              details={"login_method": "password"})
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request_body: dict, db: Session = Depends(get_db)):
    """刷新令牌"""
    refresh_token_val = request_body.get("refresh_token")
    if not refresh_token_val:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少refresh_token")
    
    payload = decode_token(refresh_token_val)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user or user.status.value != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用")
    
    new_access_token = create_access_token(data={"sub": user.user_id})
    new_refresh_token = create_refresh_token(data={"sub": user.user_id})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户信息（含权限列表）"""
    from app.schemas.schemas import UserResponse
    user_data = UserResponse.model_validate(current_user).model_dump()
    user_data["permissions"] = get_user_permissions(current_user, db)
    return {"code": 200, "data": user_data}

@router.put("/change-password")
async def change_password(
    pwd_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码（需验证旧密码）"""
    if not verify_password(pwd_data.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码不正确")
    
    if not validate_password(pwd_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码必须包含大小写字母、数字和特殊字符，且长度至少8位"
        )
    
    current_user.password_hash = get_password_hash(pwd_data.new_password)
    db.commit()
    
    from app.core.audit_log import write_log
    write_log(db, current_user.user_id, "user:change_password", "User", current_user.user_id)
    db.commit()
    
    return {"code": 200, "message": "密码修改成功"}

@router.put("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    pwd_data: AdminPasswordReset,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """管理员重置用户密码"""
    target_user = db.query(User).filter(User.user_id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    if not validate_password(pwd_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码必须包含大小写字母、数字和特殊字符，且长度至少8位"
        )
    
    target_user.password_hash = get_password_hash(pwd_data.new_password)
    db.commit()
    
    from app.core.audit_log import write_log
    write_log(db, current_user.user_id, "admin:reset_password", "User", user_id,
              before_data={"target_user": target_user.username},
              details={"operator": current_user.username})
    db.commit()
    
    return {"code": 200, "message": f"用户 {target_user.username} 的密码已重置"}

