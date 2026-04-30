/**
 * RSA 加密工具（基于浏览器原生 Web Crypto API）
 *
 * 使用 window.crypto.subtle 进行 RSA-OAEP 加密，
 * 无需引入任何第三方加密库（如 jsencrypt）。
 *
 * 用法：
 *   import { fetchPublicKeyAndEncrypt } from '@/utils/crypto-utils'
 *   const encryptedPassword = await fetchPublicKeyAndEncrypt('MyPassword123')
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
    false,
    ['encrypt']
  )
}

/**
 * 使用 RSA 公钥加密明文文本
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

  return arrayBufferToBase64(encrypted)
}

/**
 * 从后端获取 RSA 公钥并加密密码（一站式便捷函数）
 *
 * 流程：
 *   1. GET /api/v1/auth/public-key 获取公钥
 *   2. 导入为 CryptoKey 对象
 *   3. RSA-OAEP 加密密码
 *   4. 返回 Base64 密文
 *
 * @param {string} password - 用户输入的明文密码
 * @returns {Promise<string>} 加密后的密码；如果失败则返回原密码（降级）
 */
export async function fetchPublicKeyAndEncrypt(password) {
  try {
    const response = await fetch('/api/v1/auth/public-key')
    if (!response.ok) {
      console.warn('[Security] Failed to get public key, sending plain text')
      return password
    }

    const result = await response.json()

    if (result.code !== 200 || !result.data?.public_key) {
      console.warn('[Security] Invalid public key response, sending plain text')
      return password
    }

    const publicKey = await importRsaPublicKey(result.data.public_key)
    const encrypted = await rsaEncrypt(password, publicKey)
    console.log('[Security] Password encrypted successfully, length:', encrypted.length)
    return encrypted
  } catch (error) {
    console.error('[Security] RSA encryption failed:', error)
    // 降级策略：加密失败时发送原始密码（保证可用性优先）
    return password
  }
}

/**
 * ArrayBuffer 转 Base64 字符串
 */
function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (const byte of bytes) {
    binary += String.fromCharCode(byte)
  }
  return btoa(binary)
}
