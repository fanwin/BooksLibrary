"""
测试 JWT 令牌的生成和验证
"""
from app.core.security import create_access_token, decode_token
from app.core.config import settings

# 测试创建访问令牌
user_id = 1
token = create_access_token(data={"sub": user_id})
print(f"生成的令牌: {token}")

# 测试解码令牌
payload = decode_token(token)
print(f"解码后的 payload: {payload}")
print(f"用户 ID: {payload.get('sub')}")
print(f"用户 ID 类型: {type(payload.get('sub'))}")

# 测试类型转换
try:
    user_id_int = int(payload.get('sub'))
    print(f"转换后的用户 ID: {user_id_int}")
    print(f"转换后的用户 ID 类型: {type(user_id_int)}")
except ValueError as e:
    print(f"类型转换错误: {e}")
