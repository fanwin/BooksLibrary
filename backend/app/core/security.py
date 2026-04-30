"""
安全工具：密码加密、JWT令牌管理、RSA传输加密
"""
import base64
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# RSA 加密依赖（cryptography 随 python-jose[cryptography] 已安装）
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding, rsa
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# 配置passlib使用bcrypt，禁用自动后端检测以避免版本兼容问题
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__ident="2b"
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌（含会话生命周期约束）"""
    to_encode = data.copy()
    # 确保 sub 字段是字符串类型
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    
    # 会话有效期：优先使用传入的过期时间，否则使用配置中的会话生命周期
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        session_lifetime_seconds = int(expires_delta.total_seconds())
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        session_lifetime_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    now = datetime.now(timezone.utc)
    
    to_encode.update({
        "exp": expire,
        "iat": now,                          # 签发时间（用于计算剩余有效期）
        "session_exp": expire.isoformat(),   # 会话到期时间（ISO格式，前端可直接解析）
        "session_ttl": session_lifetime_seconds,  # 会话总时长（秒）
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    # 确保 sub 字段是字符串类型
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        print(f"[JWT解码错误] 类型: {type(e).__name__}, 详情: {e}")
        print(f"[JWT调试] 使用的密钥前10位: {settings.JWT_SECRET_KEY[:10]}...")
        print(f"[JWT调试] 使用的算法: {settings.JWT_ALGORITHM}")
        return None


import re

def validate_password(password: str) -> bool:
    """验证密码复杂度：大小写+数字+特殊字符≥8位"""
    if len(password) < 8:
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True


# ==================== RSA 传输加密工具 ====================
# 内存中缓存当前有效的 RSA 密钥对（用于密码传输加密）
_current_rsa_keypair = None


def generate_rsa_keypair() -> tuple:
    """
    生成 RSA-2048 密钥对（用于前端加密密码后传输）

    Returns:
        (private_key_pem, public_key_pem): 私钥和公钥的 PEM 格式字符串

    注意：
      - 公钥返回给前端，用于加密密码
      - 私钥仅保存在服务端内存，用于解密（永不外泄/持久化）
      - 每次调用都会生成新的密钥对（防重放攻击）
    """
    global _current_rsa_keypair

    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography 库未安装，无法生成RSA密钥对。请执行: pip install cryptography")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # 序列化私钥 (PKCS#8) — 仅存内存
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    # 序列化公钥 (SPKI) — 返回给前端
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    _current_rsa_keypair = {
        'private_key': private_key,
        'public_key_pem': public_pem.strip(),
        'created_at': time.time()
    }

    return private_pem, public_pem.strip()


def rsa_decrypt(encrypted_b64: str) -> str:
    """
    用当前内存中的 RSA 私钥解密 Base64 编码的密文

    Args:
        encrypted_b64: Base64 编码的 RSA-OAEP 密文字符串

    Returns:
        解密后的明文字符串

    Raises:
        ValueError: 没有可用密钥对或解密失败
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography 库未安装")
    if not _current_rsa_keypair:
        raise ValueError("No active RSA keypair. Call /auth/public-key first.")

    encrypted_bytes = base64.b64decode(encrypted_b64)
    private_key = _current_rsa_keypair['private_key']

    decrypted_bytes = private_key.decrypt(
        encrypted_bytes,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted_bytes.decode('utf-8')


def get_public_key_pem() -> str:
    """获取当前缓存的公钥 PEM（如不存在则自动生成）"""
    if _current_rsa_keypair:
        return _current_rsa_keypair['public_key_pem']
    _, pub_pem = generate_rsa_keypair()
    return pub_pem
