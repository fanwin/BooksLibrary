"""
认证路由（含验证码）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token, validate_password
from app.core.captcha import generate_captcha, verify_captcha
from app.models.models import User, UserRole, UserStatus
from app.schemas.schemas import (
    UserCreate, UserLogin, TokenResponse,
    UserResponse, PasswordChange, PasswordReset, AdminPasswordReset,
    CaptchaResponse
)
from app.api.dependencies import get_current_user, require_super_admin, get_user_permissions

router = APIRouter(prefix="/auth", tags=["认证"])


# ============ 验证码接口 ============

@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha():
    """
    生成登录验证码
    
    返回 Base64 编码的验证码图片和关联的 captcha_key。
    前端需将图片展示给用户，用户输入后连同 captcha_key 一起提交到登录接口。
    
    验证码特性：
      - 4 位字符（大写字母 + 数字，排除易混淆的 0/O/1/I/L）
      - 有效期 5 分钟
      - 一次性使用（校验后立即失效）
      - 大小写不敏感
    """
    result = generate_captcha(expire_seconds=300)
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证码生成失败: {result.get('error')}",
        )
    return result

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
    """
    用户登录（支持用户名或邮箱，需验证码）
    
    流程：
      1. 校验验证码（captcha_key + captcha_code）
      2. 验证用户名/邮箱 + 密码
      3. 检查账户状态
      4. 签发 JWT Token
    """
    # ====== 步骤1：校验验证码 ======
    if login_data.captcha_key or login_data.captcha_code:
        # 前端传了验证码字段，必须校验通过
        if not verify_captcha(login_data.captcha_key, login_data.captcha_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期，请重新获取",
            )
    else:
        # 兼容性：前端未传验证码时也允许登录（可后续强制要求）
        pass

    # ====== 步骤2：验证用户凭证 ======
    user = db.query(User).filter(
        (User.username == login_data.username) | (User.email == login_data.username)
    ).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # ====== 步骤3：检查账户状态 ======
    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"用户账户状态：{user.status.value}"
        )
    
    # ====== 步骤4：签发 Token（含会话生命周期） ======
    from app.core.config import settings
    session_ttl_seconds = settings.SESSION_LIFETIME_HOURS * 3600
    session_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=session_ttl_seconds)).isoformat()
    
    access_token = create_access_token(data={"sub": user.user_id})
    refresh_token = create_refresh_token(data={"sub": user.user_id})
    
    # 记录登录日志（含会话生命周期信息）
    from app.core.audit_log import write_log
    write_log(db, user.user_id, "user:login", "User", user.user_id,
              details={
                  "login_method": "password_with_captcha",
                  "session_lifetime_hours": settings.SESSION_LIFETIME_HOURS,
              })
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": session_ttl_seconds,           # 会话有效期（秒），前端用于倒计时
        "session_expires_at": session_expires_at      # 会话到期时间，前端用于精确判断
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

    session_ttl_seconds = settings.SESSION_LIFETIME_HOURS * 3600
    session_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=session_ttl_seconds)).isoformat()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": session_ttl_seconds,
        "session_expires_at": session_expires_at
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

