<template>
  <div class="register-container">
    <div class="register-box">
      <div class="register-header">
        <el-icon size="48" color="#409EFF"><Reading /></el-icon>
        <h1>用户注册</h1>
        <p>创建您的图书馆账户</p>
      </div>

      <!-- ====== 陷阱层：欺骗浏览器密码管理器 ====== -->
      <!-- 在可视区域内用 opacity:0 隐藏，Chrome 扫描到后会优先填充这些框 -->
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

      <el-form :model="registerForm" :rules="rules" ref="formRef" class="register-form" autocomplete="off">
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="请输入邮箱"
            size="large"
            :prefix-icon="Message"
          />
        </el-form-item>

        <!-- 密码框：永远使用 type=text + CSS text-security:disc，浏览器不识别为密码框 -->
        <el-form-item prop="password">
          <div class="pwd-field-wrapper" @click="passwordNativeRef?.focus()">
            <span class="field-prefix"><el-icon><Lock /></el-icon></span>
            <input
              ref="passwordNativeRef"
              v-model="registerForm.password"
              type="text"
              class="native-password-input"
              placeholder="请输入密码（至少8位，包含大小写字母、数字和特殊字符）"
              :style="{ '-webkit-text-security': showPassword ? 'none' : 'disc' }"
              @input="onPasswordInput"
              @keyup.enter="handleRegister"
            />
            <span class="pwd-toggle-btn" @click.stop="togglePasswordVisibility">
              <el-icon><component :is="showPassword ? 'View' : 'Hide'" /></el-icon>
            </span>
          </div>
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <div class="pwd-field-wrapper" @click="confirmPwdNativeRef?.focus()">
            <span class="field-prefix"><el-icon><Lock /></el-icon></span>
            <input
              ref="confirmPwdNativeRef"
              v-model="registerForm.confirmPassword"
              type="text"
              class="native-password-input"
              placeholder="请确认密码"
              :style="{ '-webkit-text-security': showConfirmPassword ? 'none' : 'disc' }"
              @input="onConfirmPwdInput"
              @keyup.enter="handleRegister"
            />
            <span class="pwd-toggle-btn" @click.stop="toggleConfirmPwdVisibility">
              <el-icon><component :is="showConfirmPassword ? 'View' : 'Hide'" /></el-icon>
            </span>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleRegister"
            style="width: 100%"
          >
            注册
          </el-button>
        </el-form-item>

        <div class="register-footer">
          <span>已有账号？</span>
          <router-link to="/login">立即登录</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { Reading, User, Lock, Message, View, Hide } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

// 原生 input 引用（密码框）
const passwordNativeRef = ref(null)
const confirmPwdNativeRef = ref(null)
// 陷阱输入框引用
const baitUserRef = ref(null)
const baitPassRef = ref(null)
// 陷阱数据：接收浏览器自动填充（用户不可见）
const baitUsername = ref('')
const baitPassword = ref('')

// 密码可见性切换
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const togglePasswordVisibility = () => { showPassword.value = !showPassword.value }
const toggleConfirmPwdVisibility = () => { showConfirmPassword.value = !showConfirmPassword.value }

// 输入事件触发校验
const onPasswordInput = () => { formRef.value?.validateField('password') }
const onConfirmPwdInput = () => { formRef.value?.validateField('confirmPassword') }

/** 重置表单 */
const resetForm = () => {
  registerForm.username = ''
  registerForm.email = ''
  registerForm.password = ''
  registerForm.confirmPassword = ''
  showPassword.value = false
  showConfirmPassword.value = false
}

const registerForm = reactive({
  username: '', email: '', password: '', confirmPassword: ''
})

// ========== 定时清理自动填充 ==========
let cleanTimer = null

/**
 * 每 300ms 检查真实表单字段是否被浏览器偷偷填入值。
 * Chrome 的密码管理器会在 DOM 加载后异步填充，
 * 即使是陷阱框也可能被绕过，所以需要持续清理。
 */
const startCleaner = () => {
  cleanTimer = setInterval(() => {
    // 清理陷阱框的值（防止累积）
    if (baitUsername.value) baitUsername.value = ''
    if (baitPassword.value) baitPassword.value = ''

    // 如果用户尚未主动在某个字段输入过，且该字段突然有了值 → 自动填充痕迹
  }, 300)
}

onMounted(() => {
  resetForm()
  nextTick(() => {
    startCleaner()
    // 延迟再清一次：Chrome 往往在页面完全加载后才触发自动填充
    setTimeout(resetForm, 500)
  })
})

onBeforeUnmount(() => {
  if (cleanTimer) clearInterval(cleanTimer)
})

// ========== 表单校验规则 ==========
const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请确认密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '长度在3到50个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
    { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$/,
      message: '密码必须包含大小写字母、数字和特殊字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePass, trigger: 'blur' }
  ]
}

const handleRegister = async () => {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return
    loading.value = true
    const { confirmPassword, ...data } = registerForm
    await userStore.register(data)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (error) {
    console.error('注册失败:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.register-container {
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

.register-box {
  width: 480px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(10px);
  position: relative;
  z-index: 1;
  overflow: visible;
}

/* ======== 陷阱区域：欺骗 Chrome 密码管理器 ========
 * 必须满足：
 * 1. 在 DOM 树中位于真实表单之前
 * 2. 在浏览器视口内（不能 left:-9999px，否则新版 Chrome 忽略）
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

.register-header {
  text-align: center; margin-bottom: 40px;

  h1 { font-size: 28px; color: #303133; margin: 16px 0 8px; }
  p   { font-size: 14px; color: #909399; }
}

.register-form .el-form-item { margin-bottom: 24px; }

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

.register-footer {
  text-align: center; margin-top: 16px;
  font-size: 14px; color: #606266;
  a {
    color: #409EFF; text-decoration: none; margin-left: 8px;
    &:hover { text-decoration: underline; }
  }
}
</style>
