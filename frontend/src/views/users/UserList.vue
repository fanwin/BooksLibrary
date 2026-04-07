<template>
  <div class="user-list page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增用户</el-button>
        </div>
      </template>

      <!-- 搜索筛选区 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="queryParams.keyword" placeholder="用户名/邮箱/手机/证号" clearable style="width: 220px"
            @keyup.enter="fetchUsers" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="queryParams.role" placeholder="全部角色" clearable style="width: 150px">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="采编管理员" value="catalog_admin" />
            <el-option label="流通管理员" value="circulation_admin" />
            <el-option label="读者" value="reader" />
            <el-option label="审计员" value="auditor" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status_filter" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="正常" value="active" />
            <el-option label="未激活" value="inactive" />
            <el-option label="已禁用/挂失" value="suspended" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="fetchUsers">搜索</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 用户表格 -->
      <el-table :data="users" v-loading="loading" stripe border style="width: 100%">
        <el-table-column prop="user_id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" width="120">
          <template #default="{ row }">
            <span class="username-link" @click="showDetail(row)">{{ row.username }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="130">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)" size="small">{{ getRoleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reader_card_number" label="读者证号" width="150" />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="reader_type" label="读者类型" width="100">
          <template #default="{ row }">
            {{ getReaderTypeText(row.reader_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="170" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="showDetail(row)">详情</el-button>
            <el-button size="small" type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button
              v-if="row.status === 'active'"
              size="small" type="warning" link @click="handleSuspend(row)">禁用</el-button>
            <el-button
              v-else
              size="small" type="success" link @click="handleActivate(row)">启用</el-button>
            <el-button
              v-if="row.role !== 'super_admin'"
              size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchUsers"
          @current-change="fetchUsers"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="560px"
      destroy-on-close
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" :disabled="isEdit" placeholder="3-50字符" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="form.email" placeholder="请输入邮箱" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20" v-if="!isEdit">
          <el-col :span="12">
            <el-form-item label="密码" prop="password">
              <el-input v-model="form.password" type="password" show-password
                placeholder="大小写+数字+特殊字符≥8位" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="手机号">
              <el-input v-model="form.phone" placeholder="选填" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色" prop="role">
              <el-select v-model="form.role" style="width: 100%" :disabled="isEdit && form.role === 'super_admin'">
                <el-option label="超级管理员" value="super_admin" />
                <el-option label="采编管理员" value="catalog_admin" />
                <el-option label="流通管理员" value="circulation_admin" />
                <el-option label="读者" value="reader" />
                <el-option label="审计员" value="auditor" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="读者类型" prop="reader_type">
              <el-select v-model="form.reader_type" style="width: 100%">
                <el-option label="学生" value="student" />
                <el-option label="教职工" value="staff" />
                <el-option label="社会读者" value="public" />
                <el-option label="管理员" value="admin" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="isEdit">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option label="正常" value="active" />
                <el-option label="未激活" value="inactive" />
                <el-option label="已禁用" value="suspended" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 用户详情抽屉 -->
    <el-drawer v-model="detailDrawerVisible" title="用户详情" direction="rtl" size="520px">
      <div v-if="userDetail" class="drawer-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ userDetail.user_id }}</el-descriptions-item>
          <el-descriptions-item label="用户名">{{ userDetail.username }}</el-descriptions-item>
          <el-descriptions-item label="角色">
            <el-tag :type="getRoleTagType(userDetail.role)" size="small">{{ getRoleText(userDetail.role) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="userDetail.status === 'active' ? 'success' : 'danger'" size="small">
              {{ getStatusText(userDetail.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ userDetail.email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ userDetail.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="读者证号">{{ userDetail.reader_card_number || '-' }}</el-descriptions-item>
          <el-descriptions-item label="读者类型">{{ getReaderTypeText(userDetail.reader_type) }}</el-descriptions-item>
          <el-descriptions-item label="最大借阅数">{{ userDetail.max_borrow_count || 10 }} 本</el-descriptions-item>
          <el-descriptions-item label="借阅期限">{{ userDetail.borrow_limit_days || 30 }} 天</el-descriptions-item>
          <el-descriptions-item label="当前借阅中">{{ userDetail.active_borrows || 0 }} 本</el-descriptions-item>
          <el-descriptions-item label="累计借阅">{{ userDetail.total_borrows || 0 }} 次</el-descriptions-item>
          <el-descriptions-item label="未缴罚款">¥{{ (userDetail.unpaid_fines || 0).toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="注册时间" :span="2">{{ userDetail.created_at || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 读者证操作 -->
        <div class="card-ops-section" v-if="userDetail.user_id && userDetail.role !== 'super_admin'">
          <el-divider content-position="left">读者证操作</el-divider>
          <div class="card-ops-buttons">
            <el-button size="small" type="primary" @click="handleIssueCard(userDetail.user_id)">办证</el-button>
            <el-button size="small" type="warning" @click="handleLossCard(userDetail.user_id)">挂失</el-button>
            <el-button size="small" type="success" @click="handleReplaceCard(userDetail.user_id)">补换</el-button>
          </div>
        </div>

        <!-- 管理员操作 -->
        <div class="card-ops-section" v-if="userDetail.user_id && isSuperAdmin">
          <el-divider content-position="left">管理员操作</el-divider>
          <div class="card-ops-buttons">
            <el-button size="small" type="danger" @click="handleResetPassword(userDetail)">重置密码</el-button>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="showResetPwdDialog" title="重置用户密码" width="450px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="resetPwdFormRef" :model="resetPwdForm" :rules="resetPwdRules" label-width="100px">
        <el-alert title="重置后用户需使用新密码登录" type="warning" :closable="false" show-icon style="margin-bottom: 16px" />
        <el-form-item label="用户">
          <el-input :value="resetPwdTarget?.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="resetPwdForm.new_password" type="password" show-password
            placeholder="大小写+数字+特殊字符≥8位" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="resetPwdForm.confirm_password" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showResetPwdDialog = false">取消</el-button>
        <el-button type="danger" :loading="resetPwdLoading" @click="confirmResetPassword">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const submitLoading = ref(false)
const users = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const isEdit = ref(false)
const detailDrawerVisible = ref(false)
const userDetail = ref(null)
const formRef = ref(null)

const isSuperAdmin = computed(() => localStorage.getItem('user_role') === 'super_admin')

const queryParams = reactive({
  keyword: '',
  role: '',
  status_filter: '',
  page: 1,
  size: 20,
})

const form = reactive({
  username: '', email: '', phone: '', password: '', role: 'reader', reader_type: 'student', status: 'active',
})
const editingUserId = ref(null)

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '长度在3到50个字符', trigger: 'blur' }
  ],
  email: [{ type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '至少8位', trigger: 'blur' },
  ],
}

onMounted(() => fetchUsers())

async function fetchUsers() {
  loading.value = true
  try {
    const params = {
      page: queryParams.page,
      size: queryParams.size,
    }
    if (queryParams.keyword) params.keyword = queryParams.keyword
    if (queryParams.role) params.role = queryParams.role
    if (queryParams.status_filter) params.status_filter = queryParams.status_filter

    const res = await request.get('/users', { params })
    users.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (error) {
    console.error('获取用户列表失败:', error)
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  queryParams.keyword = ''
  queryParams.role = ''
  queryParams.status_filter = ''
  queryParams.page = 1
  fetchUsers()
}

function handleAdd() {
  isEdit.value = false
  Object.assign(form, { username: '', email: '', phone: '', password: '', role: 'reader', reader_type: 'student', status: 'active' })
  dialogVisible.value = true
}

function handleEdit(row) {
  isEdit.value = true
  editingUserId.value = row.user_id
  Object.assign(form, {
    username: row.username,
    email: row.email || '',
    phone: row.phone || '',
    role: row.role,
    status: row.status,
    reader_type: row.reader_type || 'student',
    password: '',
  })
  dialogVisible.value = true
}

function resetForm() {
  formRef.value?.resetFields()
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await request.put(`/users/${editingUserId.value}`, {
        email: form.email || undefined,
        phone: form.phone || undefined,
        role: form.role,
        status: form.status,
        reader_type: form.reader_type,
      })
      ElMessage.success('用户信息已更新')
    } else {
      await request.post('/users', {
        username: form.username,
        email: form.email || undefined,
        phone: form.phone || undefined,
        password: form.password,
        role: form.role,
        reader_type: form.reader_type,
        status: form.status,
      })
      ElMessage.success('用户创建成功')
    }
    dialogVisible.value = false
    fetchUsers()
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitLoading.value = false
  }
}

async function showDetail(row) {
  try {
    const res = await request.get(`/users/${row.user_id}`)
    userDetail.value = res.data || res
    detailDrawerVisible.value = true
  } catch (e) {
    // 如果详情接口不存在，使用表格行数据
    userDetail.value = row
    detailDrawerVisible.value = true
  }
}

async function handleSuspend(row) {
  try {
    await ElMessageBox.confirm(`确定要禁用用户 "${row.username}" 吗？`, '确认禁用', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.post(`/users/${row.user_id}/suspend`)
    ElMessage.success(`用户 "${row.username}" 已被禁用`)
    fetchUsers()
  } catch (e) { /* 取消或报错 */ }
}

async function handleActivate(row) {
  try {
    await request.post(`/users/${row.user_id}/activate`)
    ElMessage.success(`用户 "${row.username}" 已被启用`)
    fetchUsers()
  } catch (e) {
    console.error('启用失败:', e)
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${row.username}" 吗？此操作不可恢复！`,
      '确认删除',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error', confirmButtonClass: 'el-button--danger' }
    )
    await request.delete(`/users/${row.user_id}`)
    ElMessage.success('用户已删除')
    fetchUsers()
  } catch (e) { /* 取消 */ }
}

// 读者证操作
async function handleIssueCard(userId) {
  try {
    const { value: readerType } = await ElMessageBox.prompt('选择读者类型办理读者证', '办证', {
      confirmButtonText: '办理',
      cancelButtonText: '取消',
      inputValue: 'student',
      inputPlaceholder: 'student/staff/public',
    })
    await request.post(`/users/${userId}/reader-card/issue`, { reader_type: readerType })
    ElMessage.success('读者证办理成功')
    fetchUsers()
    if (detailDrawerVisible.value) showDetail({ user_id: userId })
  } catch (e) { /* 取消 */ }
}

async function handleLossCard(userId) {
  try {
    await ElMessageBox.confirm('确定要挂失该用户的读者证吗？挂失后借阅功能将暂停。', '确认挂失', {
      confirmButtonText: '确认挂失', cancelButtonText: '取消', type: 'warning'
    })
    await request.post(`/users/${userId}/reader-card/loss`)
    ElMessage.success('读者证已挂失')
    fetchUsers()
    if (detailDrawerVisible.value) showDetail({ user_id: userId })
  } catch (e) { /* 取消 */ }
}

async function handleReplaceCard(userId) {
  try {
    await ElMessageBox.confirm('为该用户补换新读者证（挂失后重新发证）？', '补换读者证', {
      confirmButtonText: '确认补换', cancelButtonText: '取消', type: 'info'
    })
    await request.post(`/users/${userId}/reader-card/replace`)
    ElMessage.success('读者证补换成功')
    fetchUsers()
    if (detailDrawerVisible.value) showDetail({ user_id: userId })
  } catch (e) { /* 取消 */ }
}

// 重置密码
const showResetPwdDialog = ref(false)
const resetPwdLoading = ref(false)
const resetPwdFormRef = ref(null)
const resetPwdTarget = ref(null)
const resetPwdForm = reactive({ new_password: '', confirm_password: '' })
const resetPwdRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '至少8位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: (rule, value, callback) => {
      if (value !== resetPwdForm.new_password) callback(new Error('两次输入的密码不一致'))
      else callback()
    }, trigger: 'blur' },
  ],
}

function handleResetPassword(user) {
  resetPwdTarget.value = user
  resetPwdForm.new_password = ''
  resetPwdForm.confirm_password = ''
  showResetPwdDialog.value = true
}

async function confirmResetPassword() {
  if (!resetPwdFormRef.value) return
  try {
    await resetPwdFormRef.value.validate()
  } catch {
    return
  }
  resetPwdLoading.value = true
  try {
    await request.put(`/auth/${resetPwdTarget.value.user_id}/reset-password`, {
      new_password: resetPwdForm.new_password,
    })
    ElMessage.success(`用户「${resetPwdTarget.value.username}」的密码已重置`)
    showResetPwdDialog.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  } finally {
    resetPwdLoading.value = false
  }
}

// 辅助方法
function getRoleText(role) {
  return {
    super_admin: '超级管理员',
    catalog_admin: '采编管理员',
    circulation_admin: '流通管理员',
    reader: '读者',
    auditor: '审计员',
  }[role] || role
}

function getRoleTagType(role) {
  return {
    super_admin: 'danger', catalog_admin: '', circulation_admin: 'warning',
    reader: '', auditor: 'info',
  }[role] || ''
}

function getReaderTypeText(type) {
  return { student: '学生', staff: '教职工', public: '社会读者', admin: '管理员' }[type] || (type || '-')
}

function getStatusText(status) {
  return { active: '正常', inactive: '未激活', suspended: '已禁用/挂失' }[status] || status
}
</script>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.search-form {
  margin-bottom: 16px;
  .el-form-item { margin-bottom: 8px; }
}
.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.username-link {
  color: #409EFF;
  cursor: pointer;
  &:hover { text-decoration: underline; font-weight: 500; }
}
.drawer-content {
  padding: 0 8px;
}
.card-ops-section {
  margin-top: 24px;
  .card-ops-buttons {
    display: flex; gap: 8px;
  }
}
</style>
