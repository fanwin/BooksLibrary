import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

// 标记是否正在刷新 token
let isRefreshing = false
// 存储等待重试的请求
let failedQueue = []

// 处理队列中的请求
const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (token) {
      prom.resolve(token)
    } else {
      prom.reject(error)
    }
  })
  failedQueue = []
}

// 刷新 token 的函数
const refreshTokenRequest = async () => {
  const refresh_token = localStorage.getItem('refresh_token')
  if (!refresh_token) {
    throw new Error('No refresh token')
  }

  try {
    const response = await axios.post('/api/v1/auth/refresh', {
      refresh_token
    })

    const { access_token, refresh_token: new_refresh_token } = response.data

    // 更新本地存储的 token
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', new_refresh_token)

    return access_token
  } catch (error) {
    // 刷新失败，清除所有 token 并跳转登录
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    router.push('/login')
    throw error
  }
}

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    const res = response.data

    if (res.code && res.code !== 200) {
      ElMessage.error(res.message || '请求失败')

      // 401: 未授权，跳转登录
      if (res.code === 401) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        router.push('/login')
      }

      return Promise.reject(new Error(res.message || '请求失败'))
    }

    return res
  },
  async (error) => {
    const originalRequest = error.config

    // 如果是 401 错误且不是刷新 token 的请求本身，且尚未重试过
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/auth/refresh')) {
      if (isRefreshing) {
        // 如果正在刷新，将请求加入队列
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return request(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const newToken = await refreshTokenRequest()
        processQueue(null, newToken)

        // 使用新 token 重试原始请求
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return request(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // 其他错误处理
    if (error.response) {
      const { status, data } = error.response

      if (status === 401 && !originalRequest._retry) {
        ElMessage.error('未授权，请重新登录')
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        router.push('/login')
      } else if (status === 403) {
        ElMessage.error('权限不足')
      } else if (status === 404) {
        ElMessage.error('请求的资源不存在')
      } else if (status >= 500) {
        ElMessage.error('服务器错误')
      } else if (!originalRequest._retry) {
        ElMessage.error(data.detail || data.message || '请求失败')
      }
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }

    return Promise.reject(error)
  }
)

export default request
