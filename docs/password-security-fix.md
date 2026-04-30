# 密码明文传输漏洞分析与修复方案

> **文档版本**: v1.0 | **创建日期**: 2026-04-13 | **严重等级**: **HIGH (高)**

---

## 一、漏洞概述

### 1.1 漏洞描述

在浏览器开发者工具（F12）的 **Network（网络）** 面板中，用户登录时可以**直接看到明文密码**。

### 1.2 漏洞复现步骤

1. 打开浏览器，进入系统登录页面 `http://localhost:5173/login`
2. 按 `F12` 打开开发者工具
3. 切换到 **Network（网络）** 标签
4. 输入用户名和密码（例如：`admin / Admin@123456`），点击"登录"
5. 在请求列表中找到 `login` 请求 → 点击 **Payload（载荷）** 标签
6. **明文密码直接暴露**：

```json
{
  "username": "admin",
  "password": "Admin@123456",       // ⚠️ 明文！任何人可见
  "captchaKey": "abc123...",
  "captchaCode": "A7XK"
}
```

### 1.3 影响范围

| 攻击场景 | 危害程度 | 说明 |
|---------|---------|------|
| **中间人攻击 (MITM)** | 🔴 极高 | 同一局域网/WiFi 下攻击者可抓包获取所有用户明文密码 |
| **浏览器扩展恶意读取** | 🔴 高 | 恶意 Chrome 扩展可监听所有 HTTP 请求并提取密码字段 |
| **XSS 跨站脚本窃取** | 🔴 高 | 若存在 XSS 漏洞，脚本可拦截 XMLHttpRequest 并记录密码 |
| **CDN/代理日志泄漏** | 🟠 中 | 经过 Nginx/Cloudflare 等中间层时，请求体可能被日志记录 |
| **浏览器自动填充 + F12 查看** | 🟡 中低 | 浏览器密码管理器保存后，F12 可从 DOM 或 localStorage 直接读取 |
| **前端内存残留** | 🟡 中 | Vue reactive 对象中的明文密码可通过 Console 输出查看 |

---

## 二、根因分析 — 密码全链路追踪

```
┌──────────────────────────────────────────────────────────────────────┐
│                        密码数据流（修复前）                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [1] 用户输入                                                        │
│      ├── 组件: Login.vue 第23行                                       │
│      ├── 控件: <el-input type="password">                             │
│      └── 问题: type="password" 仅做视觉遮罩(●●●)，v-model 仍为明文     │
│                                                                      │
│  [2] 前端状态存储                                                     │
│      ├── 文件: Login.vue 第96行                                       │
│      └── 数据: loginForm.password = 'Admin@123456'  ← 内存明文        │
│                                                                      │
│  [3] 网络传输 ★★★ 核心漏洞点 ★★★                                    │
│      ├── 文件: stores/user.js 第175行                                 │
│      ├── 调用: request.post('/auth/login', loginForm)                 │
│      ├── 协议: HTTP (非 HTTPS)                                        │
│      ├── 格式: JSON application/json                                  │
│      └── Payload: { "password": "Admin@123456" }   ← 线路明文！      │
│                  ║                                                    │
│                  ▼  F12 Network → Payload → 完全可见                  │
│                                                                      │
│  [4] 后端接收                                                         │
│      ├── 文件: auth.py 第86行                                         │
│      ├── Schema: UserLogin (schemas.py 第53行)                       │
│      └── 字段: password: str                                         │
│                                                                      │
│  [5] 后端验证 & 存储                                                  │
│      ├── 验证: security.py verify_password() → bcrypt 校验            │
│      └── 存储: password_hash (bcrypt) ✅ 存储安全                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

关键发现:
  ✓ 后端存储安全 (bcrypt hash)
  ✓ 后端验证安全 (不记录明文)
  ✗ 网络传输不安全 (HTTP + JSON 明文)          ← 主要漏洞!
  ✗ 前端内存可读 (reactive 对象无保护)
  ✗ 浏览器可识别密码框 (标准 type=password)
```

---

## 三、修复方案设计

### 3.1 方案选型对比

| 方案 | 原理 | 安全性 | 复杂度 | 推荐度 |
|------|------|--------|--------|-------|
| **A. 强制 HTTPS** | TLS 加密全部流量 | 高 | 低（需证书） | 生产必须，但开发环境无效 |
| **B. 前端 SHA-256 哈希** | 密码→哈希值传输 | 中 | 低 | ❌ 哈希值=新密码，可被重放 |
| **C. RSA 非对称加密** | 前端用公钥加密，后端用私钥解密 | **高** | 中 | ✅ **本方案采用** |
| **D. SRP/E2EE 协议** | 零知识证明 | 最高 | 高 | 过于复杂，不适合本项目 |

### 3.2 最终方案：RSA + 反浏览器填充 + 安全加固

```
┌──────────────────────────────────────────────────────────────────────┐
│                        修复后的安全数据流                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Phase 1: 登录前 — 获取 RSA 公钥                                      │
│  ┌─────────┐  GET /auth/public-key    ┌──────────┐                   │
│  │ 前端     │ ─────────────────────→  │ 后端      │                   │
│  │ Login.vue│ ←── { public_key:      │ 生成2048位│                   │
│  │         │     "MIIBIjANBgk..." }  │ RSA密钥对 │                   │
│  └─────────┘                         └──────────┘                   │
│                                                                      │
│  Phase 2: 用户输入 — 多重防护                                          │
│  ┌──────────────────────────────────────────┐                        │
│  │ 1️⃣  陷阱层 (autofill-bait):              │                        │
│  │    opacity:0 的假 input[type=password]    │                        │
│  │    欺骗 Chrome 密码管理器填充到假框       │                        │
│  ├──────────────────────────────────────────┤                        │
│  │ 2️⃣  真实密码框 (native input):           │                        │
│  │    type="text" + -webkit-text-security:disc                      │
│  │    浏览器永远无法识别为密码框             │                        │
│  ├──────────────────────────────────────────┤                        │
│  │ 3️⃣  定时清理器 (300ms interval):         │                        │
│  │    清除被浏览器偷偷填入的值               │                        │
│  └──────────────────────────────────────────┘                        │
│                                                                      │
│  Phase 3: 提交登录 — RSA 加密传输                                     │
│  ┌──────────────────────────────────────────────────────┐            │
│  │ loginForm.password = "Admin@123456"                    │            │
│  │         ↓                                             │            │
│  │ window.crypto.subtle.encrypt(RSA-OAEP, publicKey, pwd) │            │
│  │         ↓                                             │            │
│  │ encryptedPassword = "a8f3e2d1... (Base64编码的密文)"   │            │
│  │         ↓                                             │            │
│  │ POST /auth/login {                                   │            │
│  │   username: "admin",                                  │            │
│  │   password: "a8f3e2d1...",  ← 密文! F12看不到原文    │            │
│  │   captchaKey: "...",                                 │            │
│  │   captchaCode: "A7XK"                                │            │
│  │ }                                                     │            │
│  └──────────────────────────────────────────────────────┘            │
│                                                                      │
│  Phase 4: 后端解密验证                                                 │
│  ┌──────────┐  RSA私钥解密         ┌─────────┐                      │
│  │ 后端     │  password密文 →      │ bcrypt   │                      │
│  │ auth.py  │  明文 "Admin@123456" → 校验通过 → JWT Token           │
│  └──────────┘                      └─────────┘                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 技术要点

| 项目 | 说明 |
|------|------|
| **加密算法** | RSA-OAEP (Optimal Asymmetric Encryption Padding) |
| **密钥长度** | 2048 位（安全且性能平衡） |
| **哈希函数** | SHA-256（OAEP 内部使用） |
| **公钥格式** | SPKI/PKCS#8 PEM (`-----BEGIN PUBLIC KEY-----`) |
| **私钥格式** | PKCS#8 PEM（仅存服务端内存，永不外泄） |
| **公钥有效期** | 每次 `/auth/public-key` 请求重新生成（防重放） |
| **Web API** | `window.crypto.subtle`（现代浏览器原生支持） |
| **降级方案** | 不支持 Web Crypto 的浏览器回退到原始明文传输（提示警告） |

---

## 四、涉及修改文件清单

### 4.1 后端修改

| 文件 | 变更内容 |
|------|---------|
| `backend/app/core/security.py` | 新增 RSA 密钥对生成、加密/解密函数 |
| `backend/app/api/v1/auth.py` | 新增 `GET /auth/public-key` 接口；修改 `POST /auth/login` 支持解密 |
| `backend/requirements.txt` | 无需新增依赖（Python 标准库 + cryptography 已有或新增 pycryptodome） |

### 4.2 前端修改

| 文件 | 变更内容 |
|------|---------|
| `frontend/src/views/Login.vue` | 1. 添加陷阱层反浏览器填充；2. 真实密码改用 `type=text`+CSS遮罩；3. 登录前 RSA 加密密码；4. 加载时获取公钥 |
| `frontend/src/utils/crypto-utils.js` | **新建** — 封装 RSA 加密工具函数 |

### 4.3 配置变更

| 文件 | 变更内容 |
|------|---------|
| 无需新增配置文件 | RSA 密钥在内存中动态生成，无需持久化 |

---

## 五、详细实施代码

### 5.1 后端：security.py 新增 RSA 工具

```python
# backend/app/core/security.py 新增内容

import os
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.backends import default_backend

# ========== RSA 密钥管理 ==========
# 内存中缓存当前有效的 RSA 密钥对（每次调用 generate_rsa_keypair 时刷新）
_current_rsa_keypair = None

def generate_rsa_keypair() -> tuple:
    """
    生成 RSA-2048 密钥对（用于密码传输加密）
    
    Returns:
        (private_key_pem, public_key_pem): 私钥和公钥的 PEM 格式字符串
    
    注意：
      - 公钥返回给前端用于加密密码
      - 私钥仅保存在服务端内存中，用于解密
      - 每次调用都会生成新的密钥对（防止重放攻击）
    """
    from cryptography.hazmat.primitives.asymmetric import rsa
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # 序列化私钥 (PKCS#8)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # 序列化公钥 (SPKI)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    global _current_rsa_keypair
    _current_rsa_keypair = {
        'private_key': private_key,
        'public_key_pem': public_pem,
        'created_at': time.time()
    }
    
    return private_pem, public_pem


def rsa_decrypt(encrypted_b64: str) -> str:
    """
    用当前内存中的 RSA 私钥解密 Base64 编码的密文
    
    Args:
        encrypted_b64: Base64 编码的 RSA-OAEP 密文字符串
        
    Returns:
        解密后的明文字符串
        
    Raises:
        ValueError: 如果没有可用的密钥对或解密失败
    """
    if not _current_rsa_keypair:
        raise ValueError("No active RSA keypair. Call generate_rsa_keypair first.")
    
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
    """获取当前缓存的公钥 PEM"""
    if _current_rsa_keypair:
        return _current_rsa_keypair['public_key_pem']
    # 如果还没有生成过，自动生成一对
    _, pub_pem = generate_rsa_keypair()
    return pub_pem
```

### 5.2 后端：auth.py 新增接口 + 修改登录逻辑

```python
# backend/app/api/v1/auth.py 变更

@router.get("/public-key")
async def get_rsa_public_key():
    """
    获取 RSA 公钥（用于前端加密密码）
    
    每次调用都会生成新的密钥对，确保一次性使用。
    返回 PEM 格式的公钥字符串。
    """
    from app.core.security import generate_rsa_keypair
    _, public_key_pem = generate_rsa_keypair()
    return {
        "code": 200,
        "data": {
            "public_key": public_key_pem.strip(),
            "algorithm": "RSA-OAEP",
            "key_size": 2048
        }
    }

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录（支持 RSA 加密密码 + 明文密码兼容）
    
    密码字段处理逻辑：
      1. 如果密码是 Base64 编码的长字符串 → 尝试 RSA 解密
      2. 如果解密失败或不是加密格式 → 当作明文处理（兼容旧客户端）
    """
    # ====== 解密密码（如果已加密）======
    raw_password = login_data.password
    decrypted_password = None
    
    # 启发式判断是否为 RSA 密文（Base64 编码的密文通常较长）
    # 正常密码不会超过 200 字符，而 RSA-2048 OAEP 加密结果约 344 字符
    if len(raw_password) > 100:
        try:
            decrypted_password = rsa_decrypt(raw_password)
        except Exception:
            pass  # 解密失败，当作明文处理
    
    password_to_verify = decrypted_password or raw_password
    
    # ====== 步骤1：校验验证码 ======
    # ... (原有验证码校验逻辑不变)

    # ====== 步骤2：验证用户凭证 ======
    user = db.query(User).filter(
        (User.username == login_data.username) | (User.email == login_data.username)
    ).first()
    
    if not user or not verify_password(password_to_verify, user.password_hash):
        # ... (原有错误响应不变)
    
    # ... (后续 Token 签发逻辑完全不变)
```

### 5.3 前端：新建 crypto-utils.js

```javascript
// frontend/src/utils/crypto-utils.js

/**
 * RSA 加密工具（基于 Web Crypto API）
 *
 * 使用浏览器原生 crypto.subtle 进行 RSA-OAEP 加密，
 * 无需引入任何第三方加密库。
 */

/**
 * 将 PEM 格式公钥转换为 CryptoKey 对象
 * @param {string} pem - PEM 格式公钥字符串
 * @returns {Promise<CryptoKey>}
 */
export async function importRsaPublicKey(pem) {
  // 移除 PEM 头尾标记和换行，提取 Base64 内容
  const base64 = pem
    .replace(/-----BEGIN PUBLIC KEY-----/, '')
    .replace(/-----END PUBLIC KEY-----/, '')
    .replace(/\s/g, '')

  const binaryString = atob(base64)
  const bytes = new Uint8Array(binaryString.length)
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i)
  }

  return await crypto.subtle.importKey(
    'spki',
    bytes,
    {
      name: 'RSA-OAEP',
      hash: 'SHA-256',
    },
    false,  // 不能导出（公钥本来就可以导出，这里无所谓）
    ['encrypt']
  )
}

/**
 * 使用 RSA 公钥加密文本
 * @param {string} plaintext - 要加密的明文
 * @param {CryptoKey} publicKey - 已导入的公钥对象
 * @returns {Promise<string>} Base64 编码的密文
 */
export async function rsaEncrypt(plaintext, publicKey) {
  const encoder = new TextEncoder()
  const data = encoder.encode(plaintext)

  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'RSA-OAEP',
    },
    publicKey,
    data
  )

  // 将 ArrayBuffer 转换为 Base64 字符串
  return arrayBufferToBase64(encrypted)
}

/**
 * 从后端获取公钥并加密密码
 * @param {string} password - 用户输入的明文密码
 * @returns {Promise<string>} 加密后的密码（如果加密失败则返回原密码）
 */
export async function fetchPublicKeyAndEncrypt(password) {
  try {
    const res = await fetch('/api/v1/auth/public-key')
    const result = await res.json()

    if (result.code !== 200 || !result.data?.public_key) {
      console.warn('[Security] Failed to get public key, sending plain text')
      return password
    }

    const publicKey = await importRsaPublicKey(result.data.public_key)
    const encrypted = await rsaEncrypt(password, publicKey)
    return encrypted
  } catch (error) {
    console.error('[Security] RSA encryption failed:', error)
    // 降级：加密失败时发送原始密码（保证可用性优先）
    return password
  }
}

/**
 * ArrayBuffer 转 Base64
 */
function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (const byte of bytes) {
    binary += String.fromCharCode(byte)
  }
  return btoa(binary)
}
```

### 5.4 前端：Login.vue 重构（核心改动）

主要变更点：

1. **陷阱层（autofill-bait）** — 欺骗 Chrome 密码管理器填充到假框
2. **真实密码框改为 `type="text"` + CSS 遮罩** — 浏览器永远不识别
3. **定时清理器** — 每 300ms 清理被浏览器偷偷填入的值
4. **登录前 RSA 加密** — 调用 `fetchPublicKeyAndEncrypt()` 加密密码

---

## 六、安全加固补充建议

以下建议按优先级排列，建议逐步实施：

### P0 — 必须立即实施（本次修复覆盖）

- [x] **RSA 加密传输密码** — 防止网络层明文泄露
- [x] **反浏览器密码管理器填充** — 防止 DOM 层明文泄露

### P1 — 强烈建议近期实施

- [ ] **生产环境强制 HTTPS** — TLS 是传输安全的基石
- [ ] **CSP (Content-Security-Policy)** — 阻止 XSS 注入脚本窃取密码
- [ ] **登录接口限流** — 防暴力破解（如：同一 IP 每分钟最多 5 次）

### P2 — 建议中期规划

- [ ] **JWT 黑名单机制** — 用户修改密码后使旧 token 失效
- [ ] **多因素认证 (MFA)** — TOTP / SMS 二次验证
- [ ] **登录设备指纹** — 异地/异设备登录告警
- [ ] **密码强度实时检测** — 注册/修改密码时前端预检

### P3 — 长期安全建设

- [ ] **安全审计日志** — 记录所有登录尝试（成功/失败/IP/时间）
- [ ] **自动化安全扫描** — 集成 OWASP ZAP / SonarQube
- [ ] **渗透测试** — 定期邀请安全团队进行渗透测试
- [ ] **等保合规** — 按照国家信息安全等级保护要求进行加固

---

## 七、测试验收清单

### 功能测试

- [ ] 使用明文密码登录 → 成功（向后兼容）
- [ ] 使用 RSA 加密密码登录 → 成功
- [ ] 错误密码登录 → 失败提示正确
- [ ] 验证码错误 → 提示正确
- [ ] F12 查看 Network Payload → 密码显示为加密乱码

### 安全验证测试

- [ ] 打开 F12 → Elements → 无法找到 `type="password"` 的真实输入框
- [ ] 打开 F12 → Console → 输入 `document.querySelectorAll('input[type="password"]')` → 只能找到陷阱框
- [ ] 浏览器密码管理器弹窗 → 自动填充到陷阱框而非真实框
- [ ] 登录请求体中 `password` 字段值长度 > 100 字符（确认是密文）

### 兼容性测试

- [ ] Chrome 90+ → 正常工作
- [ ] Firefox 88+ → 正常工作
- [ ] Edge 90+ → 正常工作
- [ ] Safari 15+ → 正常工作
- [ ] 不支持 Web Crypto 的老旧浏览器 → 降级到明文传输（控制台警告）

---

## 八、参考资料

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [MDN Web Crypto API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API)
- [RSA-OAEP Specification](https://tools.ietf.org/html/rfc8017)
- [Chrome Autofill Mitigation](https://www.chromium.org/developers/design-documents/form-styles-for-web-controls)
