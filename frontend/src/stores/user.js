import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import request from '@/utils/request'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const userInfo = ref(null)
  const permissions = ref([])

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
  }

  // 刷新令牌
  const refreshToken = async () => {
    const refresh_token = localStorage.getItem('refresh_token')
    if (!refresh_token) {
      logout()
      return
    }
    
    try {
      const res = await request.post('/auth/refresh', { refresh_token })
      token.value = res.access_token
      localStorage.setItem('access_token', res.access_token)
      localStorage.setItem('refresh_token', res.refresh_token)
    } catch (error) {
      logout()
    }
  }

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
  }
})
