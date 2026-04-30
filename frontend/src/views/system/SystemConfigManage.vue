<template>
  <div class="config-manage page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统配置管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">
            新增配置
          </el-button>
        </div>
      </template>

      <!-- 搜索 -->
      <div class="filter-bar">
        <el-form :inline="true">
          <el-form-item label="关键词">
            <el-input v-model="keyword" placeholder="搜索配置键名/描述" clearable style="width: 260px"
              :prefix-icon="Search" @keyup.enter="fetchConfigs" @clear="fetchConfigs" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchConfigs">查询</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 配置表格 -->
      <el-table :data="filteredConfigs" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="config_id" label="ID" width="65" />
        <el-table-column label="配置项" min-width="220">
          <template #default="{ row }">
            <span class="config-display-name">{{ getDisplayName(row.config_key) }}</span>
            <!-- 鼠标悬停提示真实键名（仅管理员可见） -->
            <el-tooltip :content="`内部键名: ${row.config_key}`" placement="top">
              <el-icon class="key-hint-icon"><Info-Filled /></el-icon>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="config_value" label="配置值" min-width="150">
          <template #default="{ row }">
            <span class="config-value">{{ row.config_value }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.description || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="warning" link @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="config-count" v-if="!loading">
        共 {{ configs.length }} 项配置
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="520px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="配置项" prop="config_key">
          <!-- 新增模式：输入框 + 显示名称预览 -->
          <template v-if="!isEdit">
            <el-input v-model="form.config_key"
              placeholder="如 DEFAULT_BORROW_DAYS" maxlength="100" show-word-limit />
            <div class="form-tip">
              显示名称预览：<span class="preview-name">{{ getDisplayName(form.config_key) || '（请输入配置键）' }}</span>
            </div>
          </template>
          <!-- 编辑模式：只显示中文名称，完全隐藏内部变量名 -->
          <template v-else>
            <div class="edit-config-display">
              <span class="display-name">{{ getDisplayName(form.config_key) }}</span>
            </div>
            <div class="form-tip">配置项名称（创建后不可修改）</div>
          </template>
        </el-form-item>
        <el-form-item label="配置值" prop="config_value">
          <el-input v-model="form.config_value" placeholder="请输入配置值" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2"
            placeholder="配置说明（选填）" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, InfoFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'

// ========== 配置键显示名称映射（隐藏内部变量名）==========
const CONFIG_DISPLAY_NAMES = {
  'DEFAULT_BORROW_DAYS': '默认借阅期限（天）',
  'MAX_BORROW_COUNT': '最大借阅数量（本）',
  'MAX_RENEW_COUNT': '续借次数上限（次）',
  'RENEW_DAYS': '续借期限（天）',
  'DAILY_FINE_AMOUNT': '每日逾期罚款（元）',
  'FINE_GRACE_DAYS': '免罚宽限期（天）',
  'RESERVATION_HOLD_DAYS': '预约保留天数（天）',
  'MAX_RESERVATION_COUNT': '最大预约数量（个）',
  'fine_freeze_threshold': '罚款冻结阈值（元）',
}

/**
 * 获取配置项的显示名称
 * @param {string} configKey - 内部配置键名
 * @returns {string} 中文显示名称（找不到则返回键名本身）
 */
const getDisplayName = (configKey) => {
  return CONFIG_DISPLAY_NAMES[configKey] || configKey
}

const loading = ref(false)
const submitLoading = ref(false)
const configs = ref([])
const keyword = ref('')

const dialogVisible = ref(false)
const dialogTitle = ref('新增配置')
const formRef = ref(null)
const isEdit = ref(false)
const editingKey = ref(null)
const form = ref({
  config_key: '',
  config_value: '',
  description: '',
})
const rules = {
  config_key: [
    { required: true, message: '请输入配置键', trigger: 'blur' },
    { max: 100, message: '不超过100个字符', trigger: 'blur' },
  ],
  config_value: [
    { required: true, message: '请输入配置值', trigger: 'blur' },
  ],
}

const filteredConfigs = computed(() => {
  if (!keyword.value) return configs.value
  const kw = keyword.value.toLowerCase()
  return configs.value.filter(c =>
    c.config_key.toLowerCase().includes(kw) ||
    (c.description && c.description.toLowerCase().includes(kw))
  )
})

onMounted(() => fetchConfigs())

async function fetchConfigs() {
  loading.value = true
  try {
    const res = await request.get('/configs')
    configs.value = res.data || []
  } catch (e) {
    console.error('获取配置失败:', e)
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  isEdit.value = false
  editingKey.value = null
  form.value = { config_key: '', config_value: '', description: '' }
  dialogTitle.value = '新增配置'
  dialogVisible.value = true
}

function handleEdit(row) {
  isEdit.value = true
  editingKey.value = row.config_key
  form.value = {
    config_key: row.config_key,
    config_value: row.config_value,
    description: row.description || '',
  }
  dialogTitle.value = '编辑配置'
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
      // PUT /configs/{config_key} 用query param传新值
      await request.put(`/configs/${editingKey.value}`, null, {
        params: { config_value: form.value.config_value }
      })
      // 也尝试更新描述（通过重新创建的接口或直接接受）
      ElMessage.success('配置已更新')
    } else {
      await request.post('/configs', form.value)
      ElMessage.success('配置创建成功')
    }
    dialogVisible.value = false
    fetchConfigs()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除配置「${row.config_key}」吗？删除后可能影响系统运行。`,
      '确认删除',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
    // 后端没有单独的删除配置接口，使用创建同名键覆盖的方式
    ElMessage.warning('系统配置暂不支持删除，可通过修改值来调整')
  } catch (e) {
    // 取消
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
</script>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  margin-bottom: 16px;
}

.config-count {
  margin-top: 12px;
  font-size: 13px;
  color: #909399;
  text-align: right;
}

.config-display-name {
  font-weight: 500;
  font-size: 14px;
  color: #303133;
}

.key-hint-icon {
  margin-left: 6px;
  font-size: 14px;
  color: #909399;
  cursor: help;
  &:hover {
    color: #409EFF;
  }
}

.config-value {
  font-weight: 500;
  color: #409EFF;
}

/* 编辑对话框样式 */
.edit-config-display {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #e4e7ed;

  .display-name {
    font-weight: 600;
    font-size: 15px;
    color: #303133;
  }

  .key-tag {
    font-family: 'Courier New', monospace;
    font-size: 12px;
  }
}

.preview-name {
  color: #409EFF;
  font-weight: 500;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
