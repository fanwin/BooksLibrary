<template>
  <div class="reservation-list page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>预约管理</span>
          <el-button type="primary" @click="goToBooks">
            <el-icon><Notebook /></el-icon> 去图书管理预约
          </el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-form :inline="true" :model="filterForm">
          <el-form-item label="状态">
            <el-select v-model="filterForm.status" placeholder="全部" clearable @change="fetchData">
              <el-option label="排队中" value="pending" />
              <el-option label="可取书" value="ready" />
              <el-option label="已完成" value="fulfilled" />
              <el-option label="已取消" value="cancelled" />
              <el-option label="已过期" value="expired" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchData">查询</el-button>
            <el-button @click="resetFilter">重置</el-button>
            <el-button
              v-if="isAdmin"
              type="warning"
              plain
              size="small"
              @click="handleCheckExpired"
            >检查超期预约</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-row" v-if="stats.total !== undefined">
        <div class="stat-card">
          <span class="stat-num">{{ stats.total }}</span>
          <span class="stat-label">总预约</span>
        </div>
        <div class="stat-card pending">
          <span class="stat-num">{{ stats.pending || 0 }}</span>
          <span class="stat-label">排队中（本页）</span>
        </div>
        <div class="stat-card ready">
          <span class="stat-num">{{ stats.ready || 0 }}</span>
          <span class="stat-label">待取书（本页）</span>
        </div>
        <div class="stat-card expired">
          <span class="stat-num">{{ stats.expired || 0 }}</span>
          <span class="stat-label">超时未取（本页）</span>
        </div>
      </div>

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="reservation_id" label="ID" width="70" />
        <el-table-column prop="username" label="预约读者" width="110" />
        <el-table-column prop="title" label="图书" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.title }}
            <span class="text-muted">{{ row.author }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="queue_position" label="排队位置" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.queue_position" type="info" round size="small">#{{ row.queue_position }}</el-tag>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column prop="reservation_date" label="预约时间" width="150" sortable />
        <el-table-column prop="status_text" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getReservationTagType(row.status)" effect="dark" size="small">
              {{ row.status_text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expiry_date" label="取书截止" width="120">
          <template #default="{ row }">
            <span v-if="row.expiry_date" :class="{ 'text-danger': row.is_expired }">
              {{ row.expiry_date }}
            </span>
            <span v-else>--</span>
            <el-tag
              v-if="row.status === 'ready' && !row.is_expired && row.days_until_expiry !== null"
              type="warning"
              size="small"
              style="margin-left: 4px;"
            >
              {{ row.days_until_expiry }}天后过期
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <!-- 排队中：可取消 -->
            <el-button
              v-if="row.status === 'pending'"
              link type="danger"
              size="small"
              @click="handleCancel(row)"
            >取消</el-button>
            <!-- 可取书：馆员确认取书 -->
            <el-button
              v-if="row.status === 'ready'"
              link type="success"
              size="small"
              @click="handlePickup(row)"
            >确认取书</el-button>
            <el-button
              v-if="row.status === 'ready'"
              link type="warning"
              size="small"
              @click="handleCancel(row)"
            >放弃</el-button>
            <!-- 查看排队 -->
            <el-button
              v-if="row.book_id"
              link
              type="primary"
              size="small"
              @click="showQueue(row)"
            >查看队列</el-button>
          </template>
        </el-table-column>
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

    <!-- 排队情况抽屉 -->
    <el-drawer v-model="showQueueDrawer" title="预约排队情况" direction="rtl" size="420px">
      <div v-if="queueData">
        <h4>{{ queueData.title }}（{{ queueData.available_copies }}/{{ queueData.total_copies }} 可借）</h4>
        <p class="queue-info">当前排队人数：<strong>{{ queueData.queue_length }}</strong></p>

        <el-table :data="queueData.queue" border size="small" v-if="queueData.queue.length > 0">
          <el-table-column prop="position" label="#" width="50" align="center" />
          <el-table-column prop="username" label="读者" />
          <el-table-column prop="reservation_date" label="预约时间" width="110" />
        </el-table>
        <el-empty v-else description="暂无排队" :image-size="60" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Notebook } from '@element-plus/icons-vue'
import request from '@/utils/request'

const router = useRouter()

// ============ 数据 ============
const loading = ref(false)
const tableData = ref([])
const pagination = ref({ page: 1, size: 20, total: 0 })
const filterForm = reactive({ status: '' })
const stats = ref({})
const isAdmin = computed(() => {
  const role = localStorage.getItem('user_role') || ''
  return role === 'super_admin'
})

// 队列
const showQueueDrawer = ref(false)
const queueData = ref(null)

// ============ 方法 ============

onMounted(() => fetchData())

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      size: pagination.value.size,
      status_filter: filterForm.status || undefined
    }
    const res = await request.get('/reservations', { params })
    tableData.value = res.data.items
    pagination.value.total = res.data.total

    // 计算统计
    const all = res.data.items
    stats.value = {
      total: res.data.total,
      pending: all.filter(r => r.status === 'pending').length,
      ready: all.filter(r => r.status === 'ready').length,
      expired: all.filter(r => r.is_expired).length
    }
  } catch (e) {
    console.error('获取预约列表失败:', e)
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filterForm.status = ''
  fetchData()
}

// ---- 跳转到图书管理预约 ----

function goToBooks() {
  router.push('/books')
}

// ---- 取消预约 ----

async function handleCancel(row) {
  try {
    await ElMessageBox.confirm(
      `确定要取消「${row.username}」对《${row.title}》的预约吗？`,
      '取消预约',
      { confirmButtonText: '确定取消', cancelButtonText: '再想想', type: 'warning' }
    )

    await request.post(`/reservations/${row.reservation_id}/cancel`)
    ElMessage.success('预约已取消')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '取消失败')
    }
  }
}

// ---- 确认取书 ----

async function handlePickup(row) {
  try {
    await ElMessageBox.confirm(
      `确认《${row.title}》已被 ${row.username} 取走？`,
      '取书确认',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'success' }
    )

    await request.post(`/reservations/${row.reservation_id}/pickup`)
    ElMessage.success('取书确认成功')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '操作失败')
    }
  }
}

// ---- 检查超期 ----

async function handleCheckExpired() {
  try {
    const res = await request.post('/reservations/check-expired')
    ElMessage.success(res.message)
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '检查失败')
  }
}

// ---- 查看排队 ----

async function showQueue(row) {
  try {
    const res = await request.get(`/reservations/book/${row.book_id}/queue`)
    queueData.value = res.data
    showQueueDrawer.value = true
  } catch (e) {
    ElMessage.error('获取排队信息失败')
  }
}

// ---- 工具 ----

function getReservationTagType(status) {
  const map = {
    pending: 'warning',
    ready: 'success',
    fulfilled: '',
    cancelled: 'info',
    expired: 'danger'
  }
  return map[status] || 'info'
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

.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 18px;

  .stat-card {
    background: #f5f7fa;
    padding: 12px 20px;
    border-radius: 8px;
    text-align: center;
    min-width: 100px;

    .stat-num {
      display: block;
      font-size: 24px;
      font-weight: bold;
      color: #303133;
    }

    .stat-label {
      font-size: 13px;
      color: #909399;
    }

    &.pending .stat-num { color: #E6A23C; }
    &.ready .stat-num { color: #67C23A; }
    &.expired .stat-num { color: #F56C6C; }
  }
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.text-muted {
  color: #909399;
  font-size: 12px;
  margin-left: 6px;
}

.text-danger { color: #F56C6C; }

.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  margin-top: -4px;
}

.queue-info {
  color: #606266;
  margin: 10px 0 14px;
}
</style>
