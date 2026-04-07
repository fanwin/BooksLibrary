<template>
  <div class="category-manage page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>分类管理</span>
          <div class="header-actions">
            <el-input v-model="keyword" placeholder="搜索分类名称" clearable style="width: 220px"
              :prefix-icon="Search" @keyup.enter="fetchCategories" @clear="fetchCategories" />
            <el-button type="primary" @click="handleAdd(null)">
              <el-icon><Plus /></el-icon> 新增根分类
            </el-button>
            <el-button @click="toggleExpand">
              {{ isAllExpanded ? '全部收起' : '全部展开' }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- 统计 -->
      <div class="stats-row" v-if="categoryTree.length > 0">
        <div class="stat-card">
          <span class="stat-num">{{ totalCategories }}</span>
          <span class="stat-label">总分类数</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ rootCategories }}</span>
          <span class="stat-label">一级分类</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ maxLevel }}</span>
          <span class="stat-label">最大层级</span>
        </div>
      </div>

      <!-- 树形表格 -->
      <el-table
        v-if="categoryTree.length > 0"
        :data="categoryTree"
        v-loading="loading"
        row-key="category_id"
        :default-expand-all="isAllExpanded"
        :tree-props="{ children: 'children' }"
        border
        stripe
        style="width: 100%"
        :filter-node-method="filterNode"
        ref="treeTableRef"
      >
        <el-table-column prop="category_id" label="ID" width="70" />
        <el-table-column prop="name" label="分类名称" min-width="260">
          <template #default="{ row }">
            <div class="category-name">
              <el-icon v-if="row.level === 1" color="#409EFF"><FolderOpened /></el-icon>
              <el-icon v-else color="#E6A23C"><Document /></el-icon>
              <span class="name-text">{{ row.name }}</span>
              <el-tag size="small" type="info" effect="plain" round>{{ row.level }}级</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" align="center" />
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="handleAdd(row)">添加子分类</el-button>
            <el-button size="small" type="warning" link @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-else-if="!loading" description="暂无分类数据，请添加根分类" />
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入分类名称" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="上级分类">
          <el-input :value="parentName" disabled placeholder="无（根分类）" />
        </el-form-item>
        <el-form-item label="排序号" prop="sort_order">
          <el-input-number v-model="form.sort_order" :min="0" :max="999" style="width: 100%" />
          <div class="form-tip">数值越小，排列越靠前</div>
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
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, FolderOpened, Document } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const submitLoading = ref(false)
const categoryTree = ref([])
const flatCategories = ref([])
const keyword = ref('')
const isAllExpanded = ref(true)
const treeTableRef = ref(null)

// 表单
const dialogVisible = ref(false)
const dialogTitle = ref('新增分类')
const formRef = ref(null)
const isEdit = ref(false)
const editingId = ref(null)
const parentName = ref('无（根分类）')
const form = ref({
  name: '',
  parent_id: null,
  sort_order: 0,
})
const rules = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { max: 100, message: '分类名称不超过100个字符', trigger: 'blur' },
  ],
}

// 统计
const totalCategories = computed(() => flatCategories.value.length)
const rootCategories = computed(() => flatCategories.value.filter(c => c.level === 1).length)
const maxLevel = computed(() => {
  if (flatCategories.value.length === 0) return 0
  return Math.max(...flatCategories.value.map(c => c.level))
})

onMounted(() => fetchCategories())

// 搜索过滤
watch(keyword, (val) => {
  if (treeTableRef.value) {
    treeTableRef.value.filter(val)
  }
})

function filterNode(value, data) {
  if (!value) return true
  return data.name.toLowerCase().includes(value.toLowerCase())
}

async function fetchCategories() {
  loading.value = true
  try {
    const res = await request.get('/categories')
    categoryTree.value = res.data || []
    // 构建扁平列表用于统计
    flatCategories.value = flattenTree(categoryTree.value)
  } catch (e) {
    console.error('获取分类失败:', e)
    ElMessage.error('加载分类数据失败')
  } finally {
    loading.value = false
  }
}

function flattenTree(nodes, result = []) {
  for (const node of nodes) {
    result.push(node)
    if (node.children && node.children.length > 0) {
      flattenTree(node.children, result)
    }
  }
  return result
}

function toggleExpand() {
  isAllExpanded.value = !isAllExpanded.value
  // 需要重新加载数据来触发展开/收起
  const data = categoryTree.value
  categoryTree.value = []
  setTimeout(() => {
    categoryTree.value = data
  }, 50)
}

// 新增
function handleAdd(parent) {
  isEdit.value = false
  editingId.value = null
  form.value = { name: '', parent_id: null, sort_order: 0 }
  if (parent) {
    parentName.value = parent.name
    form.value.parent_id = parent.category_id
    form.value.sort_order = (parent.children?.length || 0) * 10
    dialogTitle.value = `在「${parent.name}」下新增子分类`
  } else {
    parentName.value = '无（根分类）'
    form.value.sort_order = (rootCategories.value) * 10
    dialogTitle.value = '新增根分类'
  }
  dialogVisible.value = true
}

// 编辑
function handleEdit(row) {
  isEdit.value = true
  editingId.value = row.category_id
  form.value = {
    name: row.name,
    parent_id: row.parent_id,
    sort_order: row.sort_order,
  }
  // 找到父分类名称
  if (row.parent_id) {
    const parent = flatCategories.value.find(c => c.category_id === row.parent_id)
    parentName.value = parent ? parent.name : `ID:${row.parent_id}`
  } else {
    parentName.value = '无（根分类）'
  }
  dialogTitle.value = '编辑分类'
  dialogVisible.value = true
}

// 提交
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
      await request.put(`/categories/${editingId.value}`, form.value)
      ElMessage.success('分类已更新')
    } else {
      await request.post('/categories', form.value)
      ElMessage.success('分类创建成功')
    }
    dialogVisible.value = false
    fetchCategories()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

// 删除
async function handleDelete(row) {
  const childCount = row.children ? row.children.length : 0
  const extraMsg = childCount > 0
    ? `\n\n注意：该分类下还有 ${childCount} 个子分类，可能无法删除。`
    : ''

  try {
    await ElMessageBox.confirm(
      `确定要删除分类「${row.name}」吗？此操作不可恢复。${extraMsg}`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await request.delete(`/categories/${row.category_id}`)
    ElMessage.success('分类已删除')
    fetchCategories()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

// 格式化
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
  min-width: 100px;
  border-left: 3px solid #409EFF;

  .stat-num {
    display: block;
    font-size: 24px;
    font-weight: bold;
    color: #409EFF;
  }

  .stat-label {
    font-size: 13px;
    color: #909399;
    margin-top: 2px;
  }
}

.category-name {
  display: flex;
  align-items: center;
  gap: 8px;

  .name-text {
    font-weight: 500;
  }
}

.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin-top: 2px;
}
</style>
