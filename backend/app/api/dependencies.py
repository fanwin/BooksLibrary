"""
依赖项：认证和权限验证

角色职责划分：
  SUPER_ADMIN      - 超级管理员，拥有所有权限
  CATALOG_ADMIN    - 采编管理员，负责图书/分类/荐购管理
  CIRCULATION_ADMIN - 流通管理员，负责借阅/还书/罚款/读者证/预约管理
  READER           - 普通读者，仅可查看和操作自己的数据
  AUDITOR          - 审计员，负责日志审计和数据查看
"""
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import User, UserRole, Role
from typing import List
import json


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """获取当前已认证用户（基础认证）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise credentials_exception

    token_parts = auth_header.split(" ")
    if len(token_parts) != 2 or token_parts[0] != "Bearer":
        raise credentials_exception

    payload = decode_token(token_parts[1])
    if payload is None:
        raise credentials_exception

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise credentials_exception

    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被禁用"
        )

    return user


def get_user_permissions(user: User, db: Session) -> List[str]:
    """从 Role 表获取用户角色的权限列表"""
    from app.schemas.schemas import DEFAULT_ROLE_PERMISSIONS

    # super_admin 拥有全部权限
    if user.role.value == UserRole.SUPER_ADMIN.value:
        from app.schemas.schemas import ALL_PERMISSIONS
        return ALL_PERMISSIONS

    role_record = db.query(Role).filter(Role.role_name == user.role.value).first()
    if role_record and role_record.permissions:
        try:
            perms = json.loads(role_record.permissions)
            if isinstance(perms, list):
                return perms
        except (json.JSONDecodeError, TypeError):
            pass

    # 降级：使用硬编码默认权限
    return DEFAULT_ROLE_PERMISSIONS.get(user.role.value, [])


# ============ 细粒度权限校验 ============

def require_permission(*permissions: str):
    """基于权限字符串的细粒度校验工厂（如 require_permission('book:create', 'book:update')）"""
    async def permission_checker(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        # super_admin 直接放行
        if current_user.role.value == UserRole.SUPER_ADMIN.value:
            return current_user

        user_perms = get_user_permissions(current_user, db)
        for perm in permissions:
            if perm not in user_perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要: {', '.join(permissions)}"
                )
        return current_user
    return permission_checker


# ============ 通用角色检查 ============

def require_role(required_roles: List[str]):
    """通用权限检查工厂函数"""
    def role_checker(current_user: User = Depends(get_current_user)):
        # 超级管理员拥有所有权限
        if current_user.role.value == UserRole.SUPER_ADMIN.value:
            return current_user
        if current_user.role.value not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return role_checker


# ============ 管理员权限 ============

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """需要任意管理员权限（super_admin / catalog_admin / circulation_admin）"""
    admin_roles = [
        UserRole.SUPER_ADMIN.value,
        UserRole.CATALOG_ADMIN.value,
        UserRole.CIRCULATION_ADMIN.value,
    ]
    if current_user.role.value not in admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """仅限超级管理员"""
    if current_user.role.value != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限"
        )
    return current_user


# ============ 采编管理员权限 ============

def require_catalog_admin(current_user: User = Depends(get_current_user)) -> User:
    """需要采编管理员权限（super_admin / catalog_admin）"""
    catalog_roles = [
        UserRole.SUPER_ADMIN.value,
        UserRole.CATALOG_ADMIN.value,
    ]
    if current_user.role.value not in catalog_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要采编管理员权限"
        )
    return current_user


# ============ 流通管理员权限 ============

def require_circulation_admin(current_user: User = Depends(get_current_user)) -> User:
    """需要流通管理员权限（super_admin / circulation_admin）"""
    circulation_roles = [
        UserRole.SUPER_ADMIN.value,
        UserRole.CIRCULATION_ADMIN.value,
    ]
    if current_user.role.value not in circulation_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要流通管理员权限"
        )
    return current_user


# ============ 审计员权限 ============

def require_auditor(current_user: User = Depends(get_current_user)) -> User:
    """需要审计员权限（super_admin / auditor）"""
    auditor_roles = [
        UserRole.SUPER_ADMIN.value,
        UserRole.AUDITOR.value,
    ]
    if current_user.role.value not in auditor_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要审计员权限"
        )
    return current_user
