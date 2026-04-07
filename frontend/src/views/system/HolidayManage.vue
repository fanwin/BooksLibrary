<template>
  <div class="holiday-manage page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>节假日管理</span>
          <div class="header-actions">
            <el-select v-model="selectedYear" placeholder="选择年份" style="width: 120px" @change="fetchHolidays">
              <el-option v-for="y in yearOptions" :key="y" :label="y + '年'" :value="y" />
            </el-select>
            <el-button type="primary" :icon="Plus" @click="handleAdd">新增节假日</el-button>
            <el-button type="success" @click="showBatchDialog = true">批量导入</el-button>
          </div>
        </div>
      </template>

      <el-alert
        title="节假日说明"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      >
        <template #default>
          添加的节假日将影响应还日期计算：借阅到期日如遇节假日将自动顺延至下一个工作日。同时也跳过周末（周六、周日）。
        </template>
      </el-alert>

      <!-- 统计 -->
      <div class="stats-row" v-if="holidays.length > 0">
        <div class="stat-card">
          <span class="stat-num">{{ holidays.length }}</span>
          <span class="stat-label">{{ selectedYear }}年节假日</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ weekdayCount }}</span>
          <span class="stat-label">工作日节假日</span>
        </div>
      </div>

      <!-- 表格 -->
      <el-table :data="holidays" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="holiday_id" label="ID" width="65" />
        <el-table-column prop="date" label="日期" width="130">
          <template #default="{ row }">
            <span :class="{ 'text-danger': isPast(row.date) }">
              {{ formatDate(row.date) }}
            </span>
            <el-tag v-if="isPast(row.date)" size="small" type="info" style="margin-left: 4px">已过</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="节假日名称" min-width="200">
          <template #default="{ row }">
            <span class="holiday-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="date" label="星期" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getWeekdayType(row.date)" size="small">
              {{ getWeekday(row.date) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="warning" link @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && holidays.length === 0" description="该年份暂无节假日数据" />
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="450px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="节假日名称" prop="name">
          <el-input v-model="form.name" placeholder="如：国庆节" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="日期" prop="date">
          <el-date-picker
            v-model="form.date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="showBatchDialog" title="批量导入节假日" width="550px" :close-on-click-modal="false" destroy-on-close>
      <el-alert
        title="每行一个节假日，格式：名称,日期（YYYY-MM-DD）"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />
      <el-input
        v-model="batchText"
        type="textarea"
        :rows="10"
        placeholder="示例：
元旦,2026-01-01
春节,2026-01-28
春节,2026-01-29
春节,2026-01-30
清明节,2026-04-05
劳动节,2026-05-01"
      />
      <div class="batch-actions">
        <el-button size="small" @click="loadPreset">加载2026年预设</el-button>
      </div>
      <template #footer>
        <el-button @click="showBatchDialog = false">取消</el-button>
        <el-button type="primary" :loading="batchLoading" @click="handleBatchImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const submitLoading = ref(false)
const batchLoading = ref(false)
const holidays = ref([])
const selectedYear = ref(new Date().getFullYear())

const dialogVisible = ref(false)
const dialogTitle = ref('新增节假日')
const formRef = ref(null)
const isEdit = ref(false)
const editingId = ref(null)
const form = ref({ name: '', date: '' })
const rules = {
  name: [{ required: true, message: '请输入节假日名称', trigger: 'blur' }],
  date: [{ required: true, message: '请选择日期', trigger: 'change' }],
}

const showBatchDialog = ref(false)
const batchText = ref('')

const currentYear = new Date().getFullYear()
const yearOptions = [currentYear - 1, currentYear, currentYear + 1]

const weekdayCount = computed(() => {
  return holidays.value.filter(h => {
    const d = new Date(h.date)
    return d.getDay() !== 0 && d.getDay() !== 6
  }).length
})

onMounted(() => fetchHolidays())

async function fetchHolidays() {
  loading.value = true
  try {
    const res = await request.get('/holidays', { params: { year: selectedYear.value } })
    holidays.value = res.data || []
  } catch (e) {
    console.error('获取节假日失败:', e)
    ElMessage.error('加载节假日失败')
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  isEdit.value = false
  editingId.value = null
  form.value = { name: '', date: '' }
  dialogTitle.value = '新增节假日'
  dialogVisible.value = true
}

function handleEdit(row) {
  isEdit.value = true
  editingId.value = row.holiday_id
  form.value = { name: row.name, date: row.date }
  dialogTitle.value = '编辑节假日'
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await request.put(`/holidays/${editingId.value}`, form.value)
      ElMessage.success('节假日已更新')
    } else {
      await request.post('/holidays', form.value)
      ElMessage.success('节假日创建成功')
    }
    dialogVisible.value = false
    fetchHolidays()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${row.name}」（${formatDate(row.date)}）吗？`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await request.delete(`/holidays/${row.holiday_id}`)
    ElMessage.success('节假日已删除')
    fetchHolidays()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

function loadPreset() {
  batchText.value = `元旦,2026-01-01
春节,2026-01-28
春节,2026-01-29
春节,2026-01-30
春节,2026-01-31
春节,2026-02-01
春节,2026-02-02
春节,2026-02-03
清明节,2026-04-05
劳动节,2026-05-01
端午节,2026-06-19
中秋节,2026-09-25
国庆节,2026-10-01
国庆节,2026-10-02
国庆节,2026-10-03
国庆节,2026-10-04
国庆节,2026-10-05
国庆节,2026-10-06
国庆节,2026-10-07`
}

async function handleBatchImport() {
  const lines = batchText.value.trim().split('\n').filter(l => l.trim())
  if (lines.length === 0) {
    ElMessage.warning('请输入节假日数据')
    return
  }

  const items = []
  for (const line of lines) {
    const parts = line.split(',').map(s => s.trim())
    if (parts.length >= 2 && parts[0] && parts[1]) {
      items.push({ name: parts[0], date: parts[1] })
    }
  }

  if (items.length === 0) {
    ElMessage.warning('没有有效的节假日数据，请检查格式')
    return
  }

  batchLoading.value = true
  try {
    const res = await request.post('/holidays/batch', items)
    ElMessage.success(res.message || '批量导入完成')
    showBatchDialog.value = false
    fetchHolidays()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '批量导入失败')
  } finally {
    batchLoading.value = false
  }
}

// 辅助方法
function formatDate(dateStr) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  } catch {
    return dateStr
  }
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  try {
    return new Date(timeStr).toLocaleString('zh-CN')
  } catch {
    return timeStr
  }
}

const weekdayNames = ['日', '一', '二', '三', '四', '五', '六']

function getWeekday(dateStr) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return `周${weekdayNames[d.getDay()]}`
  } catch {
    return '-'
  }
}

function getWeekdayType(dateStr) {
  if (!dateStr) return 'info'
  try {
    const day = new Date(dateStr).getDay()
    if (day === 0 || day === 6) return 'success' // 周末调休
    return 'warning' // 工作日放假
  } catch {
    return 'info'
  }
}

function isPast(dateStr) {
  if (!dateStr) return false
  try {
    const d = new Date(dateStr)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    return d < today
  } catch {
    return false
  }
}
</script>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 18px;
}

.stat-card {
  background: #f5f7fa;
  padding: 12px 22px;
  border-radius: 8px;
  text-align: center;
  min-width: 140px;
  border-left: 3px solid #E6A23C;

  .stat-num {
    display: block;
    font-size: 24px;
    font-weight: bold;
    color: #E6A23C;
  }

  .stat-label {
    font-size: 13px;
    color: #909399;
    margin-top: 2px;
  }
}

.holiday-name {
  font-weight: 500;
}

.text-danger {
  color: #909399;
}

.batch-actions {
  margin-top: 8px;
}
</style>
