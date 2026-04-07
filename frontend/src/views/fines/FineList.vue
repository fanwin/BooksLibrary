<template>
  <div class="fine-list page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ isAdmin ? '罚款管理' : '我的罚款' }}</span>
          <div class="header-actions">
            <!-- 管理员可创建损坏/丢失罚款 -->
            <el-dropdown v-if="isAdmin" @command="handleCreateFine">
              <el-button type="primary" plain size="default">
                新建罚款 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="damage">损坏赔偿</el-dropdown-item>
                  <el-dropdown-item command="loss">丢失赔偿</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-form :inline="true" :model="filterForm">
          <el-form-item label="类型">
            <el-select v-model="filterForm.fine_type" placeholder="全部类型" clearable @change="fetchData">
              <el-option label="逾期罚款" value="overdue" />
              <el-option label="损坏赔偿" value="damage" />
              <el-option label="丢失赔偿" value="loss" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filterForm.status" placeholder="全部状态" clearable @change="fetchData">
              <el-option label="待缴纳" value="pending" />
              <el-option label="已缴纳" value="paid" />
              <el-option label="已免除" value="waived" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchData">查询</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-row" v-if="summaryData">
        <div class="stat-card pending">
          <span class="stat-num">￥{{ summaryData.pending_amount.toFixed(2) }}</span>
          <span class="stat-label">待缴总额 ({{ summaryData.pending_count }}笔)</span>
        </div>
        <div class="stat-card paid">
          <span class="stat-num">￥{{ summaryData.paid_amount.toFixed(2) }}</span>
          <span class="stat-label">已缴总额</span>
        </div>
        <div class="stat-card" :class="{ frozen: summaryData.is_frozen }">
          <span class="stat-label">{{ summaryData.can_borrow ? '借阅正常' : '⚠ 借阅被冻结' }}</span>
          <span class="stat-sub">阈值: ￥{{ summaryData.frozen_threshold }}</span>
        </div>
      </div>

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="fine_id" label="ID" width="65" />
        <el-table-column v-if="isAdmin" prop="username" label="读者" width="100" />
        <el-table-column prop="book_title" label="关联图书" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.book_title || '--' }}
          </template>
        </el-table-column>
        <el-table-column prop="fine_type_text" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getFineTypeTagType(row.fine_type)" size="small" effect="plain">
              {{ row.fine_type_text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额(￥)" width="95" align="right" sortable>
          <template #default="{ row }">
            <strong :class="{ 'text-danger': row.status === 'pending' }">
              {{ row.amount.toFixed(2) }}
            </strong>
          </template>
        </el-table-column>
        <el-table-column prop="status_text" label="状态" width="90">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'pending' ? 'danger' : row.status === 'paid' ? 'success' : 'info'"
              effect="dark"
              size="small"
            >
              {{ row.status_text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="145" sortable />
        <el-table-column prop="paid_date" label="缴纳时间" width="120">
          <template #default="{ row }">
            <span>{{ row.paid_date || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              link type="success"
              size="small"
              @click="handlePay(row)"
            >缴纳</el-button>
            <el-button
              v-if="isAdmin && row.status === 'pending'"
              link type="warning"
              size="small"
              @click="handleWaive(row)"
            >免除</el-button>
            <el-button
              link
              type="primary"
              size="small"
              @click="showDetail(row)"
            >详情</el-button>
          </template>
        </el-table-column>

        <!-- 空状态提示 -->
        <template #empty>
          <el-empty description="暂无罚款记录" />
        </template>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 缴纳对话框 -->
    <el-dialog v-model="showPayDialog" title="缴纳罚款" width="420px" :close-on-click-modal="false">
      <div v-if="payTarget" class="pay-content">
        <el-descriptions :column="1" border size="small" class="pay-desc">
          <el-descriptions-item label="读者">{{ payTarget.username }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ payTarget.fine_type_text }}</el-descriptions-item>
          <el-descriptions-item label="图书">{{ payTarget.book_title || '--' }}</el-descriptions-item>
          <el-descriptions-item label="应缴金额">
            <span class="pay-amount">￥{{ payTarget.amount.toFixed(2) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ payTarget.created_at }}</el-descriptions-item>
        </el-descriptions>

        <div class="pay-method-section">
          <h4>支付方式（模拟）</h4>
          <el-radio-group v-model="payMethod">
            <el-radio value="online">在线支付（模拟）</el-radio>
            <el-radio value="offline">线下缴纳确认</el-radio>
          </el-radio-group>
        </div>

        <el-alert
          v-if="payMethod === 'online'"
          title="模拟支付：点击确认后将直接标记为已缴纳"
          type="info"
          :closable="false"
          show-icon
          style="margin-top: 12px;"
        />
      </div>
      <template #footer>
        <el-button @click="showPayDialog = false">取消</el-button>
        <el-button type="success" :loading="payLoading" @click="confirmPay">确认缴纳</el-button>
      </template>
    </el-dialog>

    <!-- 新建罚款对话框（损坏/丢失） -->
    <el-dialog v-model="showCreateDialog" :title="createDialogTitle" width="460px" :close-on-click-modal="false">
      <el-form :model="createForm" :rules="createRules" ref="createRef" label-width="100px">
        <el-form-item label="读者ID" prop="user_id">
          <el-input-number v-model="createForm.user_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="借阅记录ID" prop="borrow_id">
          <el-input-number v-model="createForm.borrow_id" :min="1" style="width: 100%" />
          <div class="form-tip">关联的借阅记录，用于标记图书状态</div>
        </el-form-item>
        <el-form-item label="金额(￥)" prop="amount">
          <el-input-number
            v-model="createForm.amount"
            :min="0.01"
            :precision="2"
            :step="1"
            style="width: 100%"
          />
          <div class="form-tip" v-if="createForm.fine_type === 'loss'">建议填入图书定价或协商价格</div>
          <div class="form-tip" v-else>根据损坏程度协商的赔偿金额</div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreateFine">创建</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="showDetailDrawer" title="罚款详情" direction="rtl" size="450px">
      <div v-if="detailData" class="detail-content">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="罚款ID">{{ detailData.fine_id }}</el-descriptions-item>
          <el-descriptions-item label="读者">{{ detailData.username }}</el-descriptions-item>
          <el-descriptions-item label="关联图书">{{ detailData.book_title || '--' }}</el-descriptions-item>
          <el-descriptions-item label="借阅记录">{{ detailData.borrow_id || '--' }}</el-descriptions-item>
          <el-descriptions-item label="罚款类型">
            <el-tag :type="getFineTypeTagType(detailData.fine_type)" size="small">
              {{ detailData.fine_type_text }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="金额">
            <strong class="text-danger">￥{{ detailData.amount.toFixed(2) }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag
              :type="detailData.status === 'pending' ? 'danger' : detailData.status === 'paid' ? 'success' : 'info'"
              effect="dark"
              size="small"
            >
              {{ detailData.status_text }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detailData.created_at }}</el-descriptions-item>
          <el-descriptions-item label="缴纳时间">{{ detailData.paid_date || '未缴纳' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 操作日志区域 -->
        <el-divider content-position="left">操作说明</el-divider>
        <div class="detail-notes">
          <el-timeline>
            <el-timeline-item timestamp="罚款产生" placement="top" type="danger">
              <p>{{ detailData.created_at }} 生成{{ detailData.fine_type_text }}罚款 ￥{{ detailData.amount.toFixed(2) }}</p>
            </el-timeline-item>
            <el-timeline-item
              v-if="detailData.paid_date"
              timestamp="已缴纳"
              placement="top"
              type="success"
            >
              <p>{{ detailData.paid_date }} 已完成缴纳</p>
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import request from '@/utils/request'

// ============ 数据 ============
const userStore = useUserStore()
const loading = ref(false)
const tableData = ref([])
const pagination = ref({ page: 1, size: 20, total: 0 })
const filterForm = reactive({ status: '', fine_type: '' })
const summaryData = ref(null)

// 当前登录用户的角色判断
const isAdmin = computed(() => {
  const role = userStore.userRole
  return role === 'super_admin' || role === 'circulation_admin'
})

// 缴纳相关
const showPayDialog = ref(false)
const payLoading = ref(false)
const payTarget = ref(null)
const payMethod = ref('offline')

// 创建罚款相关
const showCreateDialog = ref(false)
const createLoading = ref(false)
const createRef = ref(null)
const createDialogTitle = ref('新建罚款')
const createForm = reactive({
  fine_type: '',
  user_id: null,
  borrow_id: null,
  amount: null,
  description: ''
})
const createRules = {
  user_id: [{ required: true, message: '请输入读者ID', trigger: 'blur' }],
  borrow_id: [{ required: true, message: '请输入借阅记录ID', trigger: 'blur' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }]
}

// 详情
const showDetailDrawer = ref(false)
const detailData = ref(null)

// ============ 方法 ============

onMounted(() => {
  fetchData()
  fetchSummary()
})

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      size: pagination.value.size,
      status_filter: filterForm.status || undefined,
      fine_type_filter: filterForm.fine_type || undefined
    }
    const res = await request.get('/fines', { params })
    tableData.value = res.data.items
    pagination.value.total = res.data.total
  } catch (e) {
    console.error('获取罚款列表失败:', e)
  } finally {
    loading.value = false
  }
}

async function fetchSummary() {
  try {
    const currentUserId = userStore.userId || 1
    const res = await request.get(`/users/${currentUserId}/fines/summary`)
    summaryData.value = res.data
  } catch {
    summaryData.value = null
  }
}

function resetFilter() {
  filterForm.status = ''
  filterForm.fine_type = ''
  fetchData()
}

// ---- 缴纳 ----

function handlePay(row) {
  payTarget.value = row
  payMethod.value = 'offline'
  showPayDialog.value = true
}

async function confirmPay() {
  if (!payTarget.value) return

  payLoading.value = true
  try {
    await request.post(`/fines/${payTarget.value.fine_id}/pay`, {
      amount: payTarget.value.amount,
      method: payMethod.value
    })

    const methodText = payMethod.value === 'online' ? '在线支付' : '线下缴纳'

    ElMessageBox.alert(
      `罚款已通过「${methodText}」成功缴纳<br/>金额：￥${payTarget.value.amount.toFixed(2)}<br/>时间：${new Date().toLocaleString()}`,
      '缴纳成功',
      { dangerouslyUseHTMLString: true, type: 'success' }
    )

    showPayDialog.value = false
    fetchData()
    fetchSummary()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '缴纳失败')
  } finally {
    payLoading.value = false
  }
}

// ---- 创建罚款 ----

function handleCreateFine(command) {
  createForm.fine_type = command
  if (command === 'damage') {
    createDialogTitle.value = '新建 - 损坏赔偿'
  } else {
    createDialogTitle.value = '新建 - 丢失赔偿'
  }
  resetCreateForm()
  showCreateDialog.value = true
}

function resetCreateForm() {
  createForm.user_id = null
  createForm.borrow_id = null
  createForm.amount = null
  createForm.description = ''
}

async function submitCreateFine() {
  if (!createRef.value) return
  await createRef.value.validate()

  createLoading.value = true
  try {
    let url, data
    if (createForm.fine_type === 'damage') {
      url = '/fines/damage'
      data = {
        user_id: createForm.user_id,
        borrow_id: createForm.borrow_id,
        amount: createForm.amount,
        description: createForm.description
      }
    } else {
      url = '/fines/loss'
      data = {
        user_id: createForm.user_id,
        borrow_id: createForm.borrow_id,
        amount: createForm.amount,
        description: createForm.description
      }
    }

    const res = await request.post(url, data)
    ElMessage.success(res.message || '罚款记录已创建')
    showCreateDialog.value = false
    fetchData()
    fetchSummary()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    createLoading.value = false
  }
}

// ---- 免除 ----

async function handleWaive(row) {
  try {
    await ElMessageBox.confirm(
      `确定要免除该笔￥${row.amount.toFixed(2)}的${row.fine_type_text}吗？此操作不可撤销。`,
      '确认免除',
      { confirmButtonText: '确认免除', cancelButtonText: '取消', type: 'warning' }
    )

    await request.post(`/fines/${row.fine_id}/waive`, { reason: '管理员手动免除' })
    ElMessage.success('罚款已免除')
    fetchData()
    fetchSummary()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

// ---- 详情 ----

function showDetail(row) {
  detailData.value = row
  showDetailDrawer.value = true
}

// ---- 工具 ----

function getFineTypeTagType(type) {
  const map = { overdue: 'warning', damage: '', loss: 'danger' }
  return map[type] || 'info'
}
</script>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .header-actions {
    display: flex;
    gap: 8px;
  }
}

.filter-bar {
  margin-bottom: 16px;
}

.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 18px;

  .stat-card {
    background: #f5f7fa;
    padding: 14px 22px;
    border-radius: 8px;
    min-width: 160px;
    text-align: center;
    border-left: 3px solid #dcdfe6;

    .stat-num {
      display: block;
      font-size: 22px;
      font-weight: bold;
      color: #303133;
    }

    .stat-label {
      display: block;
      font-size: 13px;
      color: #909399;
      margin-top: 2px;
    }

    .stat-sub {
      font-size: 11px;
      color: #c0c4cc;
    }

    &.pending {
      border-left-color: #E6A23C;
      .stat-num { color: #E6A23C; }
    }
    &.paid {
      border-left-color: #67C23A;
      .stat-num { color: #67C23A; }
    }
    &.frozen {
      background: #FEF0F0;
      border-left-color: #F56C6C;
      .stat-label { color: #F56C6C; font-weight: bold; }
    }
  }
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.text-danger { color: #F56C6C; }

.pay-content {
  .pay-desc { margin-bottom: 16px; }
  .pay-amount {
    font-size: 20px;
    font-weight: bold;
    color: #F56C6C;
  }
}

.pay-method-section {
  margin-top: 16px;
  h4 { font-size: 14px; margin-bottom: 10px; color: #606266; }
}

.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin-top: 2px;
}

.detail-content {
  .detail-notes {
    padding-top: 12px;
  }
}
</style>
