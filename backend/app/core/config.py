"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
import os

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "图书馆管理系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() not in ("false", "0", "release", "prod", "production", "no")
        return bool(v)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./library_management.db"
    
    # JWT配置
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    # 会话生命周期：Access Token 有效期（小时）
    SESSION_LIFETIME_HOURS: int = 1
    # Access Token 有效期（分钟），由会话生命周期换算
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 邮件配置
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = ""
    
    # 短信配置（预留）
    SMS_API_KEY: str = ""
    SMS_API_SECRET: str = ""
    
    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # 默认系统配置
    DEFAULT_BORROW_DAYS: int = 30
    MAX_BORROW_COUNT: int = 10
    MAX_RENEW_COUNT: int = 2
    RENEW_DAYS: int = 15
    DAILY_FINE_AMOUNT: float = 0.5
    FINE_GRACE_DAYS: int = 3
    RESERVATION_HOLD_DAYS: int = 3
    MAX_RESERVATION_COUNT: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
