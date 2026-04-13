import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const userInfo = ref(null)
  const permissions = ref([])

  // ========== 会话生命周期管理 ==========
  // 会话到期时间戳（毫秒），用于前端倒计时和超时检测
  const sessionExpiresAt = ref(
    localStorage.getItem('session_expires_at')
      ? parseInt(localStorage.getItem('session_expires_at'), 10)
      : 0
  )
  // 会话超时定时器引用
  let sessionTimer = null
  let warningShown = false

  /** 会话总时长（秒） */
  const SESSION_TTL_SECONDS = 3600 // 1 小时
  /** 提前警告时间（秒）—— 距离过期前多久提示用户 */
  const WARNING_BEFORE_EXPIRE = 300 // 5 分钟

  /**
   * 计算剩余会话时间（秒）
   * 负数表示已过期
   */
  const remainingSessionTime = computed(() => {
    if (!sessionExpiresAt.value) return 0
    return Math.max(0, Math.floor((sessionExpiresAt.value - Date.now()) / 1000))
  })

  /** 是否已超时 */
  const isSessionExpired = computed(() => {
    if (!sessionExpiresAt.value) return true
    return Date.now() >= sessionExpiresAt.value
  })

  /**
   * 启动会话超时监控定时器
   * 检测频率：每 30 秒检查一次
   * 行为：距离过期 5 分钟时弹窗提醒；已过期则强制登出
   */
  const startSessionMonitor = () => {
    stopSessionMonitor() // 先清除已有定时器

    sessionTimer = setInterval(() => {
      const remaining = remainingSessionTime.value

      // 已过期 → 强制登出
      if (remaining <= 0) {
        stopSessionMonitor()
        ElMessage.warning('会话已过期，请重新登录')
        forceLogout()
        return
      }

      // 距离过期 ≤ 5 分钟且尚未提醒过
      if (remaining <= WARNING_BEFORE_EXPIRE && !warningShown) {
        warningShown = true
        showSessionWarning(remaining)
      }
    }, 30000) // 每 30 秒检查一次
  }

  /** 停止会话监控 */
  const stopSessionMonitor = () => {
    if (sessionTimer) {
      clearInterval(sessionTimer)
      sessionTimer = null
    }
    warningShown = false
  }

  /** 显示即将过期的警告框 */
  const showSessionWarning = (remainingSeconds) => {
    const minutes = Math.ceil(remainingSeconds / 60)
    ElMessageBox.alert(
      `您的登录会话将在 ${minutes} 分钟后到期，是否继续操作？`,
      '会话即将到期',
      {
        confirmButtonText: '续期',
        cancelButtonText: '退出',
        type: 'warning',
        async beforeClose(action, instance, done) {
          if (action === 'confirm') {
            instance.confirmButtonLoading = true
            try {
              await refreshToken()
              done()
            } catch (e) {
              done()
            } finally {
              instance.confirmButtonLoading = false
            }
          } else if (action === 'cancel') {
            forceLogout()
            done()
          } else {
            done()
          }
        }
      }
    ).catch(() => {
      // 用户点击关闭或外部取消，不处理（下次定时器会再检测）
    })
  }

  /** 强制登出（会话过期或用户选择退出时调用） */
  const forceLogout = () => {
    logout()
    router.push('/login')
  }

  /**
   * 设置会话到期时间并启动监控
   * @param {number} expiresIn - Token 有效期（秒）
   * @param {string} sessionExpiresAtIso - ISO 格式的到期时间
   */
  const setSessionLifetime = (expiresIn, sessionExpiresAtIso = null) => {
    const ttl = expiresIn || SESSION_TTL_SECONDS
    const expiresMs = Date.now() + ttl * 1000

    sessionExpiresAt.value = expiresMs
    localStorage.setItem('session_expires_at', String(expiresMs))

    // 如果后端传了精确的到期时间，优先使用
    if (sessionExpiresAtIso) {
      const parsed = new Date(sessionExpiresAtIso).getTime()
      if (!isNaN(parsed)) {
        sessionExpiresAt.value = parsed
        localStorage.setItem('session_expires_at', String(parsed))
      }
    }

    warningShown = false
    startSessionMonitor()
  }

  /** 清除会话信息 */
  const clearSessionInfo = () => {
    sessionExpiresAt.value = 0
    localStorage.removeItem('session_expires_at')
    stopSessionMonitor()
  }

  // ========== 原有功能 ==========

  const isLoggedIn = computed(() => !!token.value)
  const userRole = computed(() => userInfo.value?.role || '')
  const username = computed(() => userInfo.value?.username || '')
  const userId = computed(() => userInfo.value?.user_id || null)

  const hasPermission = (perm) => {
    if (userRole.value === 'super_admin') return true
    return permissions.value.includes(perm)
  }

  const hasAnyPermission = (...perms) => {
    if (userRole.value === 'super_admin') return true
    return perms.some(p => permissions.value.includes(p))
  }

  const hasAllPermissions = (...perms) => {
    if (userRole.value === 'super_admin') return true
    return perms.every(p => permissions.value.includes(p))
  }

  // 登录
  const login = async (loginData) => {
    const res = await request.post('/auth/login', loginData)
    localStorage.setItem('access_token', res.access_token)
    localStorage.setItem('refresh_token', res.refresh_token)
    token.value = res.access_token

    // 设置会话生命周期
    setSessionLifetime(res.expires_in, res.session_expires_at)

    await getUserInfo()
    return res
  }

  // 注册
  const register = async (registerData) => {
    return await request.post('/auth/register', registerData)
  }

  // 获取用户信息
  const getUserInfo = async () => {
    const res = await request.get('/auth/me')
    // 兼容新旧响应格式
    if (res.code !== undefined && res.data) {
      userInfo.value = res.data
      permissions.value = res.data.permissions || []
    } else {
      userInfo.value = res
      permissions.value = res.permissions || []
    }
    return res
  }

  // 登出
  const logout = () => {
    token.value = ''
    userInfo.value = null
    permissions.value = []
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    clearSessionInfo()
  }

  // 刷新令牌
  const refreshToken = async () => {
    const refresh_token = localStorage.getItem('refresh_token')
    if (!refresh_token) {
      logout()
      throw new Error('无刷新令牌')
    }

    try {
      const res = await request.post('/auth/refresh', { refresh_token })
      token.value = res.access_token
      localStorage.setItem('access_token', res.access_token)
      localStorage.setItem('refresh_token', res.refresh_token)

      // 刷新成功后重置会话生命周期
      setSessionLifetime(res.expires_in, res.session_expires_at)
    } catch (error) {
      logout()
      throw error
    }
  }

  // 页面加载时恢复会话状态（刷新页面后恢复监控）
  const restoreSession = () => {
    if (token.value && sessionExpiresAt.value > 0) {
      // 检查保存的会话是否还有效
      if (!isSessionExpired.value) {
        startSessionMonitor()
      } else {
        clearSessionInfo()
      }
    }
  }

  // 初始化：页面加载时尝试恢复会话
  restoreSession()

  return {
    token,
    userInfo,
    permissions,
    isLoggedIn,
    userRole,
    username,
    userId,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    login,
    register,
    getUserInfo,
    logout,
    refreshToken,
    // 会话生命周期相关
    sessionExpiresAt: computed(() => sessionExpiresAt.value),
    remainingSessionTime,
    isSessionExpired,
    setSessionLifetime,
    clearSessionInfo,
    startSessionMonitor,
    stopSessionMonitor,
  }
})
