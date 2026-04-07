<template>
  <div class="purchase-requests page-container">
    <!-- 读者端：我的荐购 -->
    <el-card v-if="!isAdmin">
      <template #header>
        <div class="card-header">
          <span>我的荐购申请</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon> 发起荐购
          </el-button>
        </div>
      </template>

      <!-- 状态统计 -->
      <div class="stats-row" v-if="stats.total !== undefined">
        <div class="stat-card">
          <span class="stat-num">{{ stats.total }}</span><span class="stat-label">全部</span>
        </div>
        <div class="stat-card pending"><span class="stat-num">{{ stats.pending }}</span><span class="stat-label">待审核</span></div>
        <div class="stat-card approved"><span class="stat-num">{{ stats.approved }}</span><span class="stat-label">已通过</span></div>
        <div class="stat-card rejected"><span class="stat-num">{{ stats.rejected }}</span><span class="stat-label">被拒绝</span></div>
      </div>

      <!-- 筛选 -->
      <div class="filter-bar">
        <el-form :inline="true">
          <el-form-item label="状态">
            <el-select v-model="filterForm.status" placeholder="全部" clearable @change="fetchData">
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
              <el-option label="已采购" value="purchased" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchData">查询</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 列表 -->
      <el-table :data="tableData" v-loading="loading" border stripe style="width:100%">
        <el-table-column prop="request_id" label="ID" width="65" />
        <el-table-column prop="book_title" label="书名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="author" label="作者" width="120" show-overflow-tooltip />
        <el-table-column prop="isbn" label="ISBN" width="130" show-overflow-tooltip>
          <template #default="{ row }"><code>{{ row.isbn || '--' }}</code></template>
        </el-table-column>
        <el-table-column prop="reason" label="推荐理由" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" effect="dark" size="small">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="review_comment" label="审核意见" width="150" show-overflow-tooltip>
          <template #default="{ row }"><span>{{ row.review_comment || '--' }}</span></template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="160" />
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.size"
          :total="pagination.total" :page-sizes="[10, 20]" layout="total, sizes, prev, pager, next"
          @size-change="fetchData" @current-change="fetchData" />
      </div>
    </el-card>

    <!-- 管理员端：全部荐购管理 -->
    <el-card v-else>
      <template #header>
        <div class="card-header">
          <span>荐购审核管理</span>
          <div class="header-actions">
            <el-select v-model="filterForm.status" placeholder="全部状态" clearable size="default"
              style="width:140px" @change="fetchData">
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
              <el-option label="已采购" value="purchased" />
            </el-select>
            <el-button type="primary" @click="fetchData" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 统计卡片 -->
      <div class="stats-row admin-stats">
        <div class="stat-card pending"><span class="stat-num">{{ stats.pending || 0 }}</span><span class="stat-label">待审核</span></div>
        <div class="stat-card approved"><span class="stat-num">{{ stats.approved || 0 }}</span><span class="stat-label">已通过</span></div>
        <div class="stat-card rejected"><span class="stat-num">{{ stats.rejected || 0 }}</span><span class="stat-label">已拒绝</span></div>
        <div class="stat-card purchased"><span class="stat-num">{{ stats.purchased || 0 }}</span><span class="stat-label">已采购</span></div>
      </div>

      <el-table :data="tableData" v-loading="loading" border stripe style="width:100%">
        <el-table-column prop="request_id" label="ID" width="60" />
        <el-table-column prop="username" label="申请人" width="100" />
        <el-table-column prop="book_title" label="书名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="author" label="作者" width="110" show-overflow-tooltip />
        <el-table-column prop="isbn" label="ISBN" width="120" />
        <el-table-column prop="reason" label="推荐理由" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="95">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" effect="dark" size="small">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="155" sortable />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" link type="success" size="small"
              @click="handleReview(row, 'approved')">通过</el-button>
            <el-button v-if="row.status === 'pending'" link type="danger" size="small"
              @click="handleReview(row, 'rejected')">拒绝</el-button>
            <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.size"
          :total="pagination.total" :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next" @size-change="fetchData" @current-change="fetchData" />
      </div>
    </el-card>

    <!-- 新建荐购对话框 -->
    <el-dialog v-model="showCreateDialog" title="发起图书荐购" width="520px" :close-on-click-modal="false">
      <el-form :model="createForm" :rules="createRules" ref="createRef" label-width="90px">
        <el-alert title="请填写您希望图书馆采购的图书信息，管理员审核后决定是否纳入采购计划" type="info" :closable="false" show-icon style="margin-bottom:16px" />
        <el-form-item label="书名" prop="book_title">
          <el-input v-model="createForm.book_title" placeholder="请输入书名（必填）" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="作者">
          <el-input v-model="createForm.author" placeholder="可选" maxlength="100" />
        </el-form-item>
        <el-form-item label="ISBN">
          <el-input v-model="createForm.isbn" placeholder="可选，如 978-7-xxx" maxlength="20" />
        </el-form-item>
        <el-form-item label="推荐理由" prop="reason">
          <el-input v-model="createForm.reason" type="textarea" :rows="3" maxlength="500" show-word-limit
            placeholder="请说明为什么需要这本书..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreate">提交荐购</el-button>
      </template>
    </el-dialog>

    <!-- 审核对话框 -->
    <el-dialog v-model="showReviewDialog" :title="`审核：${currentRow?.book_title || ''}`" width="450px">
      <div v-if="currentRow">
        <el-descriptions :column="1" border size="small" class="review-info">
          <el-descriptions-item label="申请人">{{ currentRow.username || '--' }}</el-descriptions-item>
          <el-descriptions-item label="作者">{{ currentRow.author || '--' }}</el-descriptions-item>
          <el-descriptions-item label="ISBN">{{ currentRow.isbn || '--' }}</el-descriptions-item>
          <el-descriptions-item label="推荐理由">{{ currentRow.reason || '--' }}</el-descriptions-item>
          <el-descriptions-item label="申请时间">{{ currentRow.created_at }}</el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">审核操作</el-divider>
        <el-form :model="reviewForm" label-width="80px">
          <el-form-item label="审核结果">
            <el-tag :type="reviewAction === 'approved' ? 'success' : 'danger'" size="large" effect="dark">
              {{ reviewAction === 'approved' ? '✓ 通过' : '✗ 拒绝' }}
            </el-tag>
          </el-form-item>
          <el-form-item label="意见备注">
            <el-input v-model="reviewForm.review_comment" type="textarea" :rows="3"
              :placeholder="reviewAction === 'rejected' ? '请说明拒绝原因（必填）' : '可填写采购建议或备注'" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showReviewDialog = false">取消</el-button>
        <el-button :type="reviewAction === 'approved' ? 'success' : 'danger'"
          :loading="reviewLoading" @click="confirmReview">确认{{ reviewAction === 'approved' ? '通过' : '拒绝' }}</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="showDetailDrawer" title="荐购详情" direction="rtl" size="450px">
      <div v-if="detailData" class="detail-content">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="申请ID">{{ detailData.request_id }}</el-descriptions-item>
          <el-descriptions-item label="申请人">{{ detailData.username || '--' }}</el-descriptions-item>
          <el-descriptions-item label="书名">{{ detailData.book_title }}</el-descriptions-item>
          <el-descriptions-item label="作者">{{ detailData.author || '--' }}</el-descriptions-item>
          <el-descriptions-item label="ISBN"><code>{{ detailData.isbn || '--' }}</code></el-descriptions-item>
          <el-descriptions-item label="推荐理由">{{ detailData.reason || '--' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(detailData.status)" effect="dark">{{ getStatusText(detailData.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="审核意见">{{ detailData.review_comment || '--' }}</el-descriptions-item>
          <el-descriptions-item label="申请时间">{{ detailData.created_at }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ detailData.updated_at || '--' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'

// ============ 数据 ============
const loading = ref(false)
const tableData = ref([])
const pagination = ref({ page: 1, size: 20, total: 0 })
const filterForm = reactive({ status: '' })
const stats = ref({})
const isAdmin = computed(() => {
  const role = localStorage.getItem('user_role') || ''
  return ['super_admin', 'catalog_admin', 'circulation_admin'].includes(role)
})

// 创建
const showCreateDialog = ref(false)
const createLoading = ref(false)
const createRef = ref(null)
const createForm = reactive({ book_title: '', author: '', isbn: '', reason: '' })
const createRules = {
  book_title: [{ required: true, message: '请输入书名', trigger: 'blur' }],
}

// 审核
const showReviewDialog = ref(false)
const reviewLoading = ref(false)
const currentRow = ref(null)
const reviewAction = ref('')
const reviewForm = reactive({ review_comment: '' })

// 详情
const showDetailDrawer = ref(false)
const detailData = ref(null)

onMounted(() => fetchData())

// ============ 方法 ============
async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      size: pagination.value.size,
      status_filter: filterForm.status || undefined,
    }
    const res = await request.get('/purchase-requests', { params })
    tableData.value = res.data?.items || []
    pagination.value.total = res.data?.total || 0

    // 计算当前页的统计数据（读者端）
    if (!isAdmin.value) {
      const all = res.data?.items || []
      stats.value = {
        total: pagination.value.total,
        pending: all.filter(r => r.status === 'pending').length,
        approved: all.filter(r => r.status === 'approved').length,
        rejected: all.filter(r => r.status === 'rejected').length,
      }
    }
  } catch (e) {
    console.error('获取荐购列表失败:', e)
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }

  // 管理员额外获取全局统计
  if (isAdmin.value) {
    try {
      const allRes = await request.get('/purchase-requests', { params: { page: 1, size: 999 } })
      const allItems = allRes.data?.items || []
      stats.value = {
        total: allRes.data?.total || 0,
        pending: allItems.filter(r => r.status === 'pending').length,
        approved: allItems.filter(r => r.status === 'approved').length,
        rejected: allItems.filter(r => r.status === 'rejected').length,
        purchased: allItems.filter(r => r.status === 'purchased').length,
      }
    } catch { /* 静默 */ }
  }
}

function resetFilter() {
  filterForm.status = ''
  fetchData()
}

// ---- 创建 ----
async function submitCreate() {
  if (!createRef.value) return
  await createRef.value.validate()
  createLoading.value = true
  try {
    await request.post('/purchase-requests', createForm)
    ElMessage.success('荐购提交成功，等待管理员审核')
    showCreateDialog.value = false
    resetCreateForm()
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    createLoading.value = false
  }
}

function resetCreateForm() {
  createForm.book_title = ''
  createForm.author = ''
  createForm.isbn = ''
  createForm.reason = ''
}

// ---- 审核 ----
async function handleReview(row, action) {
  currentRow.value = row
  reviewAction.value = action
  reviewForm.review_comment = ''
  showReviewDialog.value = true
}

async function confirmReview() {
  if (reviewAction.value === 'rejected' && !reviewForm.review_comment.trim()) {
    ElMessage.warning('拒绝时必须填写原因')
    return
  }
  reviewLoading.value = true
  try {
    await request.put(`/purchase-requests/${currentRow.value.request_id}`, {
      status: reviewAction.value,
      review_comment: reviewForm.review_comment,
    })
    ElMessage.success(reviewAction.value === 'approved' ? '已通过荐购' : '已拒绝荐购')
    showReviewDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    reviewLoading.value = false
  }
}

// ---- 详情 ----
function showDetail(row) {
  detailData.value = row
  showDetailDrawer.value = true
}

// ---- 工具 ----
function getStatusTagType(status) {
  return { pending: 'warning', approved: 'success', rejected: 'danger', purchased: 'info' }[status] || 'info'
}
function getStatusText(status) {
  return { pending: '待审核', approved: '已通过', rejected: '已拒绝', purchased: '已采购' }[status] || status
}
</script>

<style scoped lang="scss">
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.filter-bar { margin-bottom: 16px; }
.pagination-wrapper { margin-top: 16px; display: flex; justify-content: flex-end; }

.stats-row {
  display: flex; gap: 16px; margin-bottom: 18px;
  .stat-card {
    background: #f5f7fa; padding: 12px 22px; border-radius: 8px; text-align: center; min-width: 90px;
    border-left: 3px solid #dcdfe6;
    .stat-num { display: block; font-size: 24px; font-weight: bold; color: #303133; }
    .stat-label { font-size: 13px; color: #909399; margin-top: 2px; }
    &.pending { border-left-color: #E6A23C; .stat-num { color: #E6A23C; } }
    &.approved { border-left-color: #67C23A; .stat-num { color: #67C23A; } }
    &.rejected { border-left-color: #F56C6C; .stat-num { color: #F56C6C; } }
    &.purchased { border-left-color: #409EFF; .stat-num { color: #409EFF; } }
  }
}
.admin-stats { .stat-card { min-width: 110px; } }
.review-info { margin-bottom: 16px; }
.detail-content { padding: 8px; }
</style>
