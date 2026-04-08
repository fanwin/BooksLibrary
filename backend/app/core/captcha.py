"""
验证码生成与校验模块

功能说明：
  1. 生成随机字符验证码图片（Base64 编码）
  2. 将验证码文本存储到服务端（内存/Redis），关联 captcha_key
  3. 校验用户提交的验证码是否正确
  4. 验证码一次性使用，校验后立即失效
  5. 验证码有效期默认 5 分钟

依赖：Pillow (PIL)
"""
import random
import string
import base64
import io
import hashlib
import time
from datetime import datetime, timedelta, timezone

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ============ 内存存储（生产环境建议替换为 Redis） ============
_captcha_store: dict[str, dict] = {}


def _generate_captcha_key() -> str:
    """生成唯一的验证码 key（用于前后端关联验证码）"""
    raw = f"{time.time()}-{random.randint(100000, 999999)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _cleanup_expired():
    """清理过期的验证码记录"""
    now = time.time()
    expired_keys = [
        key for key, val in _captcha_store.items()
        if now > val.get("expire_at", 0)
    ]
    for key in expired_keys:
        del _captcha_store[key]


def generate_captcha_text(length: int = 4) -> str:
    """
    生成随机验证码文本
    
    Args:
        length: 验证码字符长度，默认 4 位
        
    Returns:
        随机字符串（大写字母 + 数字，去除易混淆字符如 0/O、1/I/L）
    """
    # 排除易混淆字符: 0, O, 1, I, L
    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(random.choices(chars, k=length))


def create_captcha_image(text: str, width: int = 120, height: int = 46) -> str:
    """
    生成验证码图片并返回 Base64 编码字符串
    
    图片特征：
      - 随机背景色（浅色调）
      - 干扰线（3-5 条）
      - 干扰点（50-100 个）
      - 字符随机位置偏移
      - 字符随机轻微旋转
      
    Args:
        text: 要绘制的验证码文本
        width: 图片宽度
        height: 图片高度
        
    Returns:
        Base64 编码的 PNG 图片（不含 data:image 前缀）
        
    Raises:
        RuntimeError: 如果 Pillow 未安装
    """
    if not PIL_AVAILABLE:
        raise RuntimeError(
            "验证码生成需要安装 Pillow 库。请执行: pip install Pillow"
        )

    # 创建画布：浅色随机背景
    bg_color = (
        random.randint(230, 255),
        random.randint(230, 255),
        random.randint(240, 255),
    )
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # 绘制干扰线（3-5条）
    for _ in range(random.randint(3, 5)):
        line_color = (
            random.randint(100, 200),
            random.randint(100, 200),
            random.randint(100, 200),
        )
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=line_color, width=1)

    # 绘制干扰点（50-100个）
    for _ in range(random.randint(50, 100)):
        point_color = (
            random.randint(50, 200),
            random.randint(50, 200),
            random.randint(50, 200),
        )
        xy = (random.randint(0, width), random.randint(0, height))
        draw.point(xy, fill=point_color)

    # 绘制验证码文字
    try:
        # 尝试使用系统字体
        font_size = int(height * 0.6)
        font = ImageFont.truetype(
            "arial.ttf" if __import__("platform").system() == "Windows" else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            font_size,
        )
    except (OSError, IOError):
        # 回退到默认字体
        font = ImageFont.load_default()

    char_width = width // len(text)
    for i, ch in enumerate(text):
        # 随机字符颜色（深色调，确保可读性）
        char_color = (
            random.randint(20, 100),
            random.randint(20, 100),
            random.randint(20, 120),
        )

        # 计算字符位置（带随机偏移）
        x = int(char_width * i + char_width * 0.15 + random.randint(-3, 3))
        y = int(height * 0.15 + random.randint(-3, 5))

        # 轻微旋转效果通过绘制位置模拟
        draw.text((x, y), ch, font=font, fill=char_color)

    # 转为 Base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def generate_captcha(expire_seconds: int = 300) -> dict:
    """
    完整生成一次验证码（含存储）
    
    Args:
        expire_seconds: 验证码有效时间（秒），默认 5 分钟
        
    Returns:
        {
            "captcha_key": "str",      # 用于校验时的唯一标识
            "captcha_image": "base64",  # Base64 编码的 PNG 图片
            "expire_in": int             # 有效期秒数
        }
    """
    # 清理过期数据
    _cleanup_expired()

    text = generate_captcha_text()
    captcha_key = _generate_captcha_key()

    try:
        image_b64 = create_captcha_image(text)
    except RuntimeError as e:
        # Pillow 不可用时返回纯文本作为降级方案
        import json
        return {
            "captcha_key": "",
            "captcha_image": "",
            "error": str(e),
            "fallback_text": text,
        }

    # 存储验证码信息
    _captcha_store[captcha_key] = {
        "text": text,
        "created_at": time.time(),
        "expire_at": time.time() + expire_seconds,
        "used": False,
    }

    return {
        "captcha_key": captcha_key,
        "captcha_image": image_b64,
        "expire_in": expire_seconds,
    }


def verify_captcha(captcha_key: str, user_input: str) -> bool:
    """
    校验用户输入的验证码
    
    规则：
      - 大小写不敏感（统一转大写比较）
      - 验证码只能使用一次（用过后自动失效）
      - 过期的验证码校验失败
      
    Args:
        captcha_key: 生成验证码时返回的唯一标识
        user_input: 用户输入的验证码文本
        
    Returns:
        True: 验证码正确
        False: 验证码错误/已过期/已使用/key 不存在
    """
    if not captcha_key or not user_input:
        return False

    record = _captcha_store.get(captcha_key)

    if not record:
        return False

    # 检查是否已使用
    if record.get("used"):
        del _captcha_store[captcha_key]
        return False

    # 检查是否过期
    if time.time() > record.get("expire_at", 0):
        del _captcha_store[captcha_key]
        return False

    # 校验验证码（大小写不敏感）
    if user_input.strip().upper() != record["text"].upper():
        return False

    # 校验成功后立即标记为已使用（一次性）
    record["used"] = True
    del _captcha_store[captcha_key]

    return True


def get_captcha_stats() -> dict:
    """
    获取验证码统计信息（用于调试/监控）
    
    Returns:
        当前存储中的验证码数量等统计
    """
    _cleanup_expired()
    now = time.time()
    total = len(_captcha_store)
    active = sum(1 for v in _captcha_store.values() if not v["used"] and now < v["expire_at"])
    used = sum(1 for v in _captcha_store.values() if v["used"])
    return {
        "total_stored": total,
        "active": active,
        "used": used,
    }
