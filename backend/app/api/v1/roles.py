"""
角色权限管理路由 (RBAC)
支持超级管理员动态创建/编辑角色及权限分配
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.models.models import Role, User, UserRole
from app.schemas.schemas import (
    RoleCreate, RoleUpdate, RoleResponse,
    ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
)
from app.api.dependencies import get_current_user, require_super_admin
import json

router = APIRouter(prefix="/roles", tags=["角色权限管理"])


@router.get("", response_model=dict)
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有角色列表（含权限）"""
    roles = db.query(Role).all()
    items = []
    for r in roles:
        perms = []
        try:
            perms = json.loads(r.permissions) if r.permissions else []
        except (json.JSONDecodeError, TypeError):
            pass
        items.append({
            "role_id": r.role_id,
            "role_name": r.role_name,
            "permissions": perms,
            "description": r.description,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": len(items),
            "all_permissions": ALL_PERMISSIONS,
            "default_permissions": DEFAULT_ROLE_PERMISSIONS,
        }
    }


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个角色详情"""
    role = db.query(Role).filter(Role.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    return role


@router.post("", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """创建新角色并分配权限"""
    existing = db.query(Role).filter(Role.role_name == role_data.role_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色名已存在")

    permissions_json = json.dumps(role_data.permissions or [], ensure_ascii=False)

    new_role = Role(
        role_name=role_data.role_name,
        permissions=permissions_json,
        description=role_data.description,
    )

    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    from app.core.audit_log import write_log
    write_log(db, current_user.user_id, "role:create", "Role", new_role.role_id,
              details={"role_name": role_data.role_name, "permissions": role_data.permissions})
    db.commit()

    return new_role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """更新角色信息及权限分配"""
    role = db.query(Role).filter(Role.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    before_perms = role.permissions

    update_fields = role_data.model_dump(exclude_unset=True)
    for key, value in update_fields.items():
        if key == "permissions" and value is not None:
            setattr(role, key, json.dumps(value, ensure_ascii=False))
        else:
            setattr(role, key, value)

    db.commit()
    db.refresh(role)

    from app.core.audit_log import write_log
    write_log(db, current_user.user_id, "role:update", "Role", role_id,
              before_data={"permissions": before_perms},
              after_data={"permissions": role.permissions},
              details={"role_name": role.role_name})
    db.commit()

    return role


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """删除角色（需确保无用户使用该角色）"""
    role = db.query(Role).filter(Role.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 检查是否有内置角色保护
    builtin_roles = {"super_admin", "catalog_admin", "circulation_admin", "reader", "auditor"}
    if role.role_name in builtin_roles:
        raise HTTPException(status_code=400, detail=f"不能删除系统内置角色：{role.role_name}")

    # 检查是否有用户使用此角色
    users_with_role = db.query(User).filter(User.role == UserRole(role.role_name) if hasattr(UserRole, role.role_name) else False).count()
    # 由于 role 是 enum，这里做宽松检查
    try:
        enum_val = UserRole(role.role_name)
        users_count = db.query(User).filter(User.role == enum_val).count()
        if users_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"仍有 {users_count} 名用户使用此角色，无法删除"
            )
    except ValueError:
        pass  # 非 enum 角色名，允许删除

    db.delete(role)

    from app.core.audit_log import write_log
    write_log(db, current_user.user_id, "role:delete", "Role", role_id,
              before_data={"role_name": role.role_name, "permissions": role.permissions})
    db.commit()

    return {"code": 200, "message": "角色已删除"}


@router.get("/init/default-roles", response_model=dict)
async def init_default_roles(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    初始化默认角色到 roles 表（将硬编码的枚举角色同步为数据库中的 RBAC 角色）
    超级管理员调用一次即可完成初始化
    """
    created = 0
    updated = 0
    for role_name, permissions in DEFAULT_ROLE_PERMISSIONS.items():
        existing = db.query(Role).filter(Role.role_name == role_name).first()
        perms_json = json.dumps(permissions, ensure_ascii=False)
        if existing:
            existing.permissions = perms_json
            updated += 1
        else:
            descriptions = {
                "super_admin": "超级管理员 - 拥有所有权限",
                "catalog_admin": "采编管理员 - 图书和分类管理",
                "circulation_admin": "流通管理员 - 借阅、读者证、预约管理",
                "reader": "普通读者 - 借阅和预约",
                "auditor": "审计员 - 日志审计",
            }
            new_role = Role(
                role_name=role_name,
                permissions=perms_json,
                description=descriptions.get(role_name),
            )
            db.add(new_role)
            created += 1

    db.commit()

    from app.core.audit_log import write_log
    write_log(db, current_user.user_id, "role:init_default", None, None,
              details={"created": created, "updated": updated})
    db.commit()

    return {
        "code": 200,
        "message": f"默认角色初始化完成：新建 {created} 个，更新 {updated} 个"
    }
