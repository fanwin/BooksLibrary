<template>
  <div class="profile page-container">
    <!-- 展示模式 -->
    <el-card v-if="!isEditing">
      <template #header>
        <div class="card-header">
          <span>个人中心</span>
          <el-button type="primary" size="small" @click="startEdit">编辑信息</el-button>
        </div>
      </template>

      <el-descriptions :column="2" border v-if="userStore.userInfo">
        <el-descriptions-item label="用户名">{{ userStore.userInfo.username }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ getRoleText(userStore.userInfo.role) }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ userStore.userInfo.email || '未设置' }}</el-descriptions-item>
        <el-descriptions-item label="读者类型">{{ getReaderTypeText(userStore.userInfo.reader_type) }}</el-descriptions-item>
        <el-descriptions-item label="读者证号">{{ userStore.userInfo.reader_card_number || '未办理' }}</el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ formatTime(userStore.userInfo.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 编辑模式 -->
    <el-card v-else>
      <template #header>
        <div class="card-header">
          <span>编辑个人信息</span>
          <el-button size="small" @click="cancelEdit">取消</el-button>
        </div>
      </template>

      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="100px" style="max-width: 600px;">
        <el-form-item label="用户名">
          <el-input :value="userStore.userInfo?.username" disabled />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="editForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saveLoading" @click="saveProfile">保存修改</el-button>
          <el-button @click="cancelEdit">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 修改密码 -->
    <el-card style="margin-top: 20px;">
      <template #header><span>修改密码</span></template>

      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="100px" style="max-width: 500px;">
        <el-form-item label="当前密码" prop="old_password">
          <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" show-password
            placeholder="大小写+数字+特殊字符≥8位" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="pwdForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="warning" :loading="pwdLoading" @click="changePassword">修改密码</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import request from '@/utils/request'

const userStore = useUserStore()

// ====== 编辑信息 ======
const isEditing = ref(false)
const editFormRef = ref(null)
const saveLoading = ref(false)
const editForm = reactive({
  email: '',
  phone: '',
})

const editRules = {
  email: [{ type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }],
}

function startEdit() {
  if (userStore.userInfo) {
    editForm.email = userStore.userInfo.email || ''
    editForm.phone = userStore.userInfo.phone || ''
  }
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
  editFormRef.value?.resetFields()
}

async function saveProfile() {
  try {
    await editFormRef.value.validate()
  } catch { return }

  saveLoading.value = true
  try {
    // 使用 PUT /users/{id} 更新自己的信息
    const data = {}
    if (editForm.email) data.email = editForm.email
    if (editForm.phone) data.phone = editForm.phone

    await request.put(`/users/${userStore.userInfo.user_id}`, data)
    ElMessage.success('个人信息已更新')
    isEditing.value = false
    // 刷新用户信息
    await userStore.getUserInfo()
  } catch (error) {
    console.error('更新失败:', error)
  } finally {
    saveLoading.value = false
  }
}

// ====== 修改密码 ======
const pwdFormRef = ref(null)
const pwdLoading = ref(false)
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const validateConfirmPwd = (rule, value, callback) => {
  if (value === '') callback(new Error('请再次输入新密码'))
  else if (value !== pwdForm.new_password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const validateNewPwdComplexity = (rule, value, callback) => {
  if (value && value.length >= 8) {
    const hasLower = /[a-z]/.test(value)
    const hasUpper = /[A-Z]/.test(value)
    const hasDigit = /\d/.test(value)
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(value)
    if (!hasLower || !hasUpper || !hasDigit || !hasSpecial) {
      callback(new Error('需包含大小写字母、数字和特殊字符'))
      return
    }
  }
  callback()
}

const pwdRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '至少8位', trigger: 'blur' },
    { validator: validateNewPwdComplexity, trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPwd, trigger: 'blur' },
  ],
}

async function changePassword() {
  try {
    await pwdFormRef.value.validate()
  } catch { return }

  pwdLoading.value = true
  try {
    await request.put('/auth/change-password', {
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    ElMessage.success('密码修改成功，下次登录时生效')

    // 清空表单
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
    pwdFormRef.value?.resetFields()
  } catch (error) {
    console.error('修改密码失败:', error)
  } finally {
    pwdLoading.value = false
  }
}

// 辅助方法
function getRoleText(role) {
  return {
    super_admin: '超级管理员',
    catalog_admin: '采编管理员',
    circulation_admin: '流通管理员',
    reader: '读者',
    auditor: '系统审计员',
  }[role] || role
}

function getReaderTypeText(type) {
  return { student: '学生', staff: '教职工', public: '社会读者', admin: '管理员' }[type] || (type || '未设置')
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  try { return new Date(timeStr).toLocaleString('zh-CN') } catch { return timeStr }
}
</script>

<style scoped lang="scss">
.card-header {
  display: flex; justify-content: space-between; align-items: center;
}
</style>
