"""
操作日志审计工具
提供统一的方法在所有敏感操作中记录审计日志（只增不改）
"""
from sqlalchemy.orm import Session
from app.models.models import SystemLog
import json
from typing import Optional, Any


def write_log(
    db: Session,
    operator_id: int,
    operation_type: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
    before_data: Optional[Any] = None,
    after_data: Optional[Any] = None,
):
    """
    写入操作审计日志

    Args:
        db: 数据库会话
        operator_id: 操作人ID
        operation_type: 操作类型 (如 user:create, book:delete, borrow:return 等)
        target_type: 目标对象类型 (如 User, Book, BorrowRecord)
        target_id: 目标对象ID
        ip_address: 操作IP地址
        details: 操作详情(字典)
        before_data: 操作前数据快照(会被序列化为JSON)
        after_data: 操作后数据快照(会被序列化为JSON)
    """
    log_entry = SystemLog(
        operator_id=operator_id,
        operation_type=operation_type,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
        details=json.dumps(details, ensure_ascii=False) if details else None,
        before_data=_serialize(before_data) if before_data is not None else None,
        after_data=_serialize(after_data) if after_data is not None else None,
    )
    db.add(log_entry)
    # 不在此处 commit，由调用者统一提交事务


def _serialize(data) -> str:
    """将数据序列化为JSON字符串，支持ORM对象和字典"""
    if data is None:
        return None
    if isinstance(data, dict):
        return json.dumps(data, ensure_ascii=False, default=str)
    # ORM对象：取 __dict__ 并排除 SQLAlchemy 内部属性
    if hasattr(data, '__dict__'):
        obj_dict = {
            k: v for k, v in data.__dict__.items()
            if not k.startswith('_sa_')
        }
        return json.dumps(obj_dict, ensure_ascii=False, default=str)
    return json.dumps(str(data), ensure_ascii=False)
