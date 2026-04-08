<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <el-icon size="48" color="#409EFF"><Reading /></el-icon>
        <h1>图书馆管理系统</h1>
        <p>Library Management System</p>
      </div>
      
      <el-form :model="loginForm" :rules="rules" ref="formRef" class="login-form">
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <!-- 验证码区域 -->
        <el-form-item prop="captchaCode">
          <div class="captcha-wrapper">
            <el-input
              v-model="loginForm.captchaCode"
              placeholder="请输入验证码"
              size="large"
              :prefix-icon="Key"
              class="captcha-input"
              maxlength="4"
              @keyup.enter="handleLogin"
            />
            <div class="captcha-image-box" @click="refreshCaptcha" title="点击刷新验证码">
              <img
                v-if="captchaImageUrl"
                :src="captchaImageUrl"
                alt="验证码"
                class="captcha-img"
              />
              <div v-else class="captcha-loading">
                <el-icon class="is-loading"><Loading /></el-icon>
                加载中...
              </div>
            </div>
          </div>
          <div class="captcha-tip">看不清？<span class="refresh-link" @click="refreshCaptcha">换一张</span></div>
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
            style="width: 100%"
          >
            登录
          </el-button>
        </el-form-item>
        
        <div class="login-footer">
          <span>还没有账号？</span>
          <router-link to="/register">立即注册</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { Reading, User, Lock, Key, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
  captchaKey: '',
  captchaCode: ''
})

// 验证码相关状态
const captchaImageUrl = ref('')

/**
 * 获取验证码
 * 调用后端 /auth/captcha 接口，获取 Base64 图片和 captcha_key
 */
const fetchCaptcha = async () => {
  try {
    captchaImageUrl.value = ''
    const response = await axios.get('/api/v1/auth/captcha')
    const data = response.data
    loginForm.captchaKey = data.captcha_key
    // 拼接 data:image 前缀用于 img 标签展示
    captchaImageUrl.value = `data:image/png;base64,${data.captcha_image}`
  } catch (error) {
    console.error('获取验证码失败:', error)
    // 验证码获取失败时允许继续登录（降级处理）
    loginForm.captchaKey = ''
    captchaImageUrl.value = ''
  }
}

/** 刷新验证码（用户点击或登录失败后自动调用） */
const refreshCaptcha = () => {
  loginForm.captchaCode = ''  // 清空用户已输入的验证码
  fetchCaptcha()
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' }
  ],
  captchaCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 4, message: '请输入4位验证码', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return
    
    loading.value = true
    await userStore.login(loginForm)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error) {
    console.error('登录失败:', error)
    // 登录失败后自动刷新验证码（防止暴力破解）
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

// 页面加载时获取验证码
onMounted(() => {
  fetchCaptcha()
})
</script>

<style scoped lang="scss">
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
    background-size: 50px 50px;
    animation: move 20s linear infinite;
  }
}

@keyframes move {
  0% {
    transform: translate(0, 0);
  }
  100% {
    transform: translate(-50px, -50px);
  }
}

.login-box {
  width: 420px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(10px);
  position: relative;
  z-index: 1;
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
  
  h1 {
    font-size: 28px;
    color: #303133;
    margin: 16px 0 8px;
  }
  
  p {
    font-size: 14px;
    color: #909399;
  }
}

.login-form {
  .el-form-item {
    margin-bottom: 24px;
  }
}

// 验证码区域样式
.captcha-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;

  .captcha-input {
    flex: 1;

    :deep(.el-input__inner) {
      letter-spacing: 4px;  /* 验证码字符间距 */
    }
  }

  .captcha-image-box {
    width: 120px;
    height: 42px;
    border-radius: 6px;
    overflow: hidden;
    cursor: pointer;
    border: 1px solid #dcdfe6;
    transition: border-color 0.2s;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fafafa;

    &:hover {
      border-color: #409eff;

      .captcha-refresh-hint {
        opacity: 1;
      }
    }

    .captcha-img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }

    .captcha-loading {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      font-size: 12px;
      color: #909399;
      height: 100%;
      width: 100%;
    }
  }
}

.captcha-tip {
  line-height: 1;
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  text-align: right;

  .refresh-link {
    color: #409eff;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }
}

.login-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: #606266;
  
  a {
    color: #409EFF;
    text-decoration: none;
    margin-left: 8px;
    
    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
