<template>
  <div class="system-logs page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>操作审计日志</span>
          <el-button type="success" :icon="Download" @click="handleExport" :loading="exportLoading">导出CSV</el-button>
        </div>
      </template>

      <!-- 筛选区 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="操作类型">
          <el-select v-model="queryParams.operation_type" placeholder="全部操作" clearable style="width: 180px">
            <el-option label="用户创建" value="user:create" />
            <el-option label="用户更新" value="user:update" />
            <el-option label="用户删除" value="user:delete" />
            <el-option label="用户禁用" value="user:suspend" />
            <el-option label="用户启用" value="user:activate" />
            <el-option label="用户登录" value="user:login" />
            <el-option label="密码修改" value="user:change_password" />
            <el-option label="密码重置" value="admin:reset_password" />
            <el-option label="图书创建" value="book:create" />
            <el-option label="图书更新/删除" value="book:update" />
            <el-option label="图书删除" value="book:delete" />
            <el-option label="借书" value="borrow:create" />
            <el-option label="还书" value="borrow:return" />
            <el-option label="续借" value="borrow:renew" />
            <el-option label="读者证办理" value="reader_card:issue" />
            <el-option label="读者证挂失" value="reader_card:loss" />
            <el-option label="读者证补换" value="reader_card:replace" />
            <el-option label="角色管理" value="role:create" />
            <el-option label="角色更新" value="role:update" />
            <el-option label="角色删除" value="role:delete" />
            <el-option label="配置变更" value="config:update" />
            <el-option label="分类变更" value="category:" />
            <el-option label="日志导出" value="log:export" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            :shortcuts="dateShortcuts"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 360px"
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="queryParams.keyword" placeholder="搜索操作详情" clearable style="width: 200px"
            @keyup.enter="fetchLogs" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="fetchLogs">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 日志表格 -->
      <el-table :data="logs" v-loading="loading" stripe border style="width: 100%" size="small">
        <el-table-column prop="log_id" label="ID" width="65" />
        <el-table-column prop="operation_type" label="操作类型" width="160">
          <template #default="{ row }">
            <el-tag :type="getOpTypeTagType(row.operation_type)" size="small">
              {{ getOpTypeText(row.operation_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operator_id" label="操作人ID" width="85" />
        <el-table-column prop="target_type" label="目标对象" width="90" />
        <el-table-column prop="target_id" label="目标ID" width="75" />
        <el-table-column prop="ip_address" label="IP地址" width="140" show-overflow-tooltip />
        <el-table-column prop="operation_time" label="操作时间" width="170" sortable>
          <template #default="{ row }">{{ formatTime(row.operation_time) }}</template>
        </el-table-column>
        <el-table-column prop="details" label="操作详情" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.details_parsed" class="detail-json">
              {{ formatDetail(row.details_parsed) }}
            </span>
            <span v-else>{{ row.details || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="showLogDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.size"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchLogs"
          @current-change="fetchLogs"
        />
      </div>
    </el-card>

    <!-- 日志详情对话框 -->
    <el-dialog v-model="detailVisible" title="日志详情" width="640px" destroy-on-close>
      <div v-if="currentLog" class="log-detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="日志ID">{{ currentLog.log_id }}</el-descriptions-item>
          <el-descriptions-item label="操作类型">
            <el-tag size="small">{{ currentLog.operation_type }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="操作人ID">{{ currentLog.operator_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="目标对象">{{ currentLog.target_type || '-' }} ({{ currentLog.target_id || '-' }})</el-descriptions-item>
          <el-descriptions-item label="IP地址">{{ currentLog.ip_address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="操作时间">{{ formatTime(currentLog.operation_time) }}</el-descriptions-item>
        </el-descriptions>

        <!-- 操作详情 -->
        <div v-if="currentLog.details_parsed" class="detail-section">
          <el-divider content-position="left">操作详情</el-divider>
          <pre class="json-pre">{{ JSON.stringify(currentLog.details_parsed, null, 2) }}</pre>
        </div>
        <div v-else-if="currentLog.details" class="detail-section">
          <el-divider content-position="left">操作详情</el-divider>
          <p>{{ currentLog.details }}</p>
        </div>

        <el-alert title="审计说明" type="info" :closable="false" show-icon style="margin-top: 16px">
          <template #default>
            此日志为只读记录，不可修改或删除。审计员角色仅可查看，超级管理员可查看并导出。
          </template>
        </el-alert>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Download } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const exportLoading = ref(false)
const logs = ref([])
const total = ref(0)
const detailVisible = ref(false)
const currentLog = ref(null)
const dateRange = ref(null)

const queryParams = reactive({
  operation_type: '',
  start_date: '',
  end_date: '',
  page: 1,
  size: 20,
})

const dateShortcuts = [
  {
    text: '最近1小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setHours(start.getHours() - 1)
      return [start, end]
    },
  },
  {
    text: '今天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setHours(0, 0, 0, 0)
      return [start, end]
    },
  },
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 7)
      return [start, end]
    },
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 30)
      return [start, end]
    },
  },
]

onMounted(() => fetchLogs())

async function fetchLogs() {
  loading.value = true
  try {
    const params = {
      page: queryParams.page,
      size: queryParams.size,
    }
    if (queryParams.operation_type) params.operation_type = queryParams.operation_type
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }

    // keyword 通过 URL 参数传递（后端支持）
    if (queryParams.keyword) params.keyword = queryParams.keyword

    const res = await request.get('/logs', { params })
    logs.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (error) {
    console.error('获取日志失败:', error)
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  queryParams.operation_type = ''
  queryParams.page = 1
  dateRange.value = null
  fetchLogs()
}

async function handleExport() {
  exportLoading.value = true
  try {
    const params = {}
    if (queryParams.operation_type) params.operation_type = queryParams.operation_type
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }

    const response = await fetch('/api/v1/logs/export' + new URLSearchParams(params), {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
    })
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit_logs_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('日志导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  } finally {
    exportLoading.value = false
  }
}

function showLogDetail(row) {
  currentLog.value = row
  detailVisible.value = true
}

// 辅助方法
function formatTime(timeStr) {
  if (!timeStr) return '-'
  try {
    return new Date(timeStr).toLocaleString('zh-CN')
  } catch { return timeStr }
}

function formatDetail(parsed) {
  if (!parsed || typeof parsed !== 'object') return '-'
  return Object.entries(parsed)
    .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
    .join('; ')
}

function getOpTypeText(type) {
  const map = {
    'user:create': '创建用户', 'user:update': '更新用户', 'user:delete': '删除用户',
    'user:suspend': '禁用用户', 'user:activate': '启用用户', 'user:login': '用户登录',
    'user:change_password': '修改密码', 'admin:reset_password': '管理员重置密码',
    'book:create': '创建图书', 'book:update': '更新图书', 'book:delete': '删除图书',
    'borrow:create': '借书', 'borrow:return': '还书', 'borrow:renew': '续借',
    'borrow:approve': '借阅审批',
    'reader_card:issue': '办证', 'reader_card:loss': '挂失', 'reader_card:replace': '补换',
    'reader_card:read': '查看读者证',
    'role:create': '创建角色', 'role:update': '更新角色', 'role:delete': '删除角色', 'role:init_default': '初始化角色',
    'config:create': '创建配置', 'config:update': '更新配置',
    'category:create': '创建分类', 'category:update': '更新分类', 'category:delete': '删除分类',
    'purchase:review': '审核荐购',
    'log:read': '查看日志', 'log:export': '导出日志',
  }
  return map[type] || type.replace(':', ':').split(':')[1] || type
}

function getOpTypeTagType(type) {
  if (!type) return ''
  if (type.startsWith('user:') && type.includes('delete')) return 'danger'
  if (type.startsWith('user:') && (type.includes('suspend') || type.includes('reset'))) return 'warning'
  if (type.startsWith('book:') && type.includes('delete')) return 'danger'
  if (type.startsWith('role:') && type.includes('delete')) return 'danger'
  if (type === 'reader_card:loss') return 'warning'
  if (type.startsWith('borrow:')) return ''
  if (type === 'user:login') return 'info'
  if (type === 'log:export') return 'info'
  return ''
}
</script>

<style scoped lang="scss">
.card-header {
  display: flex; justify-content: space-between; align-items: center;
}
.search-form {
  margin-bottom: 16px;
  .el-form-item { margin-bottom: 8px; }
}
.pagination-wrapper {
  margin-top: 16px; display: flex; justify-content: flex-end;
}
.detail-json { font-size: 12px; color: #606266; }
.detail-section { margin-top: 12px; }
.json-pre {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  max-height: 300px;
}
.log-detail { padding: 0 4px; }
</style>
