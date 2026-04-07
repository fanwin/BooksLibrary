"""
数据库初始化脚本
"""
from app.core.database import engine, Base, SessionLocal
from app.models.models import User, UserRole, UserStatus, SystemConfig
from app.core.security import get_password_hash

def init_db():
    """初始化数据库并创建默认数据"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 检查是否已存在超级管理员
        admin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
        if not admin:
            # 创建默认超级管理员
            admin = User(
                username="admin",
                password_hash=get_password_hash("Admin@123456"),
                email="admin@library.com",
                role=UserRole.SUPER_ADMIN,
                status=UserStatus.ACTIVE,
                reader_type="admin"
            )
            db.add(admin)
            
            # 创建默认采编管理员
            catalog_admin = User(
                username="catalog_admin",
                password_hash=get_password_hash("Catalog@123"),
                email="catalog@library.com",
                role=UserRole.CATALOG_ADMIN,
                status=UserStatus.ACTIVE,
                reader_type="staff"
            )
            db.add(catalog_admin)
            
            # 创建默认流通管理员
            circulation_admin = User(
                username="circulation_admin",
                password_hash=get_password_hash("Circulation@123"),
                email="circulation@library.com",
                role=UserRole.CIRCULATION_ADMIN,
                status=UserStatus.ACTIVE,
                reader_type="staff"
            )
            db.add(circulation_admin)
            
            # 创建默认读者
            reader = User(
                username="reader",
                password_hash=get_password_hash("Reader@123"),
                email="reader@library.com",
                role=UserRole.READER,
                status=UserStatus.ACTIVE,
                reader_type="student",
                reader_card_number="RD20260001"
            )
            db.add(reader)
            
            print("创建默认用户账户：")
            print("  超级管理员: admin / Admin@123456")
            print("  采编管理员: catalog_admin / Catalog@123")
            print("  流通管理员: circulation_admin / Circulation@123")
            print("  读者: reader / Reader@123")
        
        # 创建默认系统配置
        default_configs = [
            ("DEFAULT_BORROW_DAYS", "30", "默认借阅期限（天）"),
            ("MAX_BORROW_COUNT", "10", "最大借阅数量"),
            ("MAX_RENEW_COUNT", "2", "续借次数上限"),
            ("RENEW_DAYS", "15", "续借期限（天）"),
            ("DAILY_FINE_AMOUNT", "0.5", "每日逾期罚款（元）"),
            ("FINE_GRACE_DAYS", "3", "免罚天数"),
            ("RESERVATION_HOLD_DAYS", "3", "预约保留天数"),
            ("MAX_RESERVATION_COUNT", "3", "最大预约数量"),
            ("fine_freeze_threshold", "50", "累计罚款冻结阈值（元），超过此金额自动冻结借阅权限"),
        ]
        
        for key, value, desc in default_configs:
            existing = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            if not existing:
                config = SystemConfig(
                    config_key=key,
                    config_value=value,
                    description=desc
                )
                db.add(config)
        
        db.commit()
        print("数据库初始化完成！")
        
    except Exception as e:
        db.rollback()
        print(f"数据库初始化失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
