<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <el-icon size="48" color="#409EFF"><Reading /></el-icon>
        <h1>图书馆管理系统</h1>
        <p>Library Management System</p>
      </div>

      <!-- ====== 陷阱层：欺骗浏览器密码管理器 ====== -->
      <!-- Chrome 扫描到 type=password 的 input 会尝试自动填充。
           我们在真实表单前放一个 opacity:0 的假密码框，
           让 Chrome 把密码填到假框里（用户不可见）。 -->
      <div class="autofill-bait">
        <label class="bait-label">Username</label>
        <input
          ref="baitUserRef"
          v-model="baitUsername"
          class="bait-input"
          tabindex="-1"
          @focus="(e) => e.target.blur()"
        />
        <label class="bait-label">Password</label>
        <input
          ref="baitPassRef"
          type="password"
          v-model="baitPassword"
          class="bait-input"
          tabindex="-1"
          @focus="(e) => e.target.blur()"
        />
      </div>

      <el-form :model="loginForm" :rules="rules" ref="formRef" class="login-form" autocomplete="off">
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>

        <!-- 密码框：type="text" + CSS text-security:disc，浏览器永远不识别为密码框 -->
        <el-form-item prop="password">
          <div class="pwd-field-wrapper" @click="passwordNativeRef?.focus()">
            <span class="field-prefix"><el-icon><Lock /></el-icon></span>
            <input
              ref="passwordNativeRef"
              v-model="loginForm.password"
              type="text"
              class="native-password-input"
              placeholder="请输入密码（至少8位）"
              :style="{ '-webkit-text-security': showPassword ? 'none' : 'disc' }"
              @keyup.enter="handleLogin"
            />
            <span class="pwd-toggle-btn" @click.stop="togglePasswordVisibility">
              <el-icon><component :is="showPassword ? 'View' : 'Hide'" /></el-icon>
            </span>
          </div>
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
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { Reading, User, Lock, Key, Loading, View, Hide } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { fetchPublicKeyAndEncrypt } from '@/utils/crypto-utils'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

// 原生 input 引用（真实密码框）
const passwordNativeRef = ref(null)
// 陷阱输入框引用
const baitUserRef = ref(null)
const baitPassRef = ref(null)
// 陷阱数据：接收浏览器自动填充（用户不可见）
const baitUsername = ref('')
const baitPassword = ref('')

// 密码可见性切换
const showPassword = ref(false)
const togglePasswordVisibility = () => { showPassword.value = !showPassword.value }

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
 */
const fetchCaptcha = async () => {
  try {
    captchaImageUrl.value = ''
    const response = await axios.get('/api/v1/auth/captcha')
    const data = response.data
    loginForm.captchaKey = data.captcha_key
    captchaImageUrl.value = `data:image/png;base64,${data.captcha_image}`
  } catch (error) {
    console.error('获取验证码失败:', error)
    loginForm.captchaKey = ''
    captchaImageUrl.value = ''
  }
}

/** 刷新验证码 */
const refreshCaptcha = () => {
  loginForm.captchaCode = ''
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

/**
 * 登录处理（含 RSA 加密）
 *
 * 流程：
 *   1. 表单校验
 *   2. 获取 RSA 公钥并加密密码
 *   3. 发送登录请求（密码已加密）
 */
const handleLogin = async () => {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    loading.value = true

    // ===== 核心：RSA 加密密码 =====
    // 从后端获取公钥 → Web Crypto API 加密 → 提交密文
    const encryptedPassword = await fetchPublicKeyAndEncrypt(loginForm.password)

    // 构建提交数据（用加密后的密码替换明文）
    const submitData = {
      username: loginForm.username,
      password: encryptedPassword,
      captchaKey: loginForm.captchaKey || undefined,
      captchaCode: loginForm.captchaCode || undefined,
    }

    await userStore.login(submitData)
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

// ========== 定时清理自动填充（防 Chrome 密码管理器绕过陷阱层）==========
let cleanTimer = null

const startCleaner = () => {
  cleanTimer = setInterval(() => {
    // 清理陷阱框的值（防止累积）
    if (baitUsername.value) baitUsername.value = ''
    if (baitPassword.value) baitPassword.value = ''

    // 如果真实字段被偷偷填入且用户未主动操作过，清理之
  }, 300)
}

onMounted(() => {
  nextTick(() => {
    startCleaner()
    // 延迟再清一次：Chrome 往往在页面完全加载后才触发自动填充
    setTimeout(() => {
      if (baitUsername.value) baitUsername.value = ''
      if (baitPassword.value) baitPassword.value = ''
    }, 500)
  })
  fetchCaptcha()
})

onBeforeUnmount(() => {
  if (cleanTimer) clearInterval(cleanTimer)
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
  0% { transform: translate(0, 0); }
  100% { transform: translate(-50px, -50px); }
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
  overflow: visible; /* 允许陷阱层定位 */
}

/* ======== 陷阱区域：欺骗 Chrome 密码管理器 ========
 * 满足条件：
 * 1. 在 DOM 树中位于真实表单之前
 * 2. 浏览器视口内可见（不能 left:-9999px，否则新版 Chrome 忽略）
 * 3. 有 label + input[type=password] 结构
 * 4. 用户看不到（opacity:0 + height:0 overflow:hidden）
 */
.autofill-bait {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 0;
  overflow: hidden;
  opacity: 0;
  z-index: -1;
  pointer-events: none;

  .bait-label {
    display: block; font-size: 12px; color: transparent;
  }
  .bait-input {
    display: block; width: 100%; height: 30px; margin-bottom: 6px;
    border: 1px solid transparent; background: transparent;
    color: transparent; font-size: 14px; outline: none;
    pointer-events: none;
    &:focus { outline: none; }
  }
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

/* ======== 自定义密码输入框（原生 HTML input） ========
 * 核心：type 永远是 "text"，用 CSS -webkit-text-security: disc 模拟遮罩
 * 这样 Chrome 密码管理器永远无法识别它为密码框！
 */
.pwd-field-wrapper {
  display: flex; align-items: center; width: 100%;
  border: 1px solid var(--el-border-color);
  border-radius: var(--el-border-radius-base);
  background-color: var(--el-fill-color-blank);
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
  font-size: var(--el-font-size-base);

  &:hover { border-color: var(--el-border-color-hover); }
  &:focus-within {
    border-color: var(--el-color-primary);
    box-shadow: 0 0 0 1px var(--el-input-focusBorderColor) inset;
  }

  .field-prefix {
    display: inline-flex; align-items: center;
    padding-left: 11px; color: var(--el-text-color-placeholder);
    flex-shrink: 0;
    .el-icon { font-size: 16px; }
  }

  .native-password-input {
    flex: 1; border: none; outline: none;
    padding: 4px 11px; height: 40px; line-height: 40px;
    font-size: inherit; background: transparent;
    color: var(--el-text-color-regular);

    &::placeholder { color: var(--el-text-color-placeholder); }
    /* CSS 密码遮罩：让 text 类型的 input 显示为 ●●● */
    -webkit-text-security: disc;
    text-security: disc;
  }

  .pwd-toggle-btn {
    display: flex; align-items: center; justify-content: center;
    padding: 0 10px; cursor: pointer;
    color: var(--el-text-color-secondary); flex-shrink: 0;
    &:hover { color: var(--el-color-primary); }
    .el-icon { font-size: 16px; }
  }
}

/* 验证码区域样式 */
.captcha-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;

  .captcha-input {
    flex: 1;

    :deep(.el-input__inner) {
      letter-spacing: 4px;
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
