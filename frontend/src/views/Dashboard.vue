<template>
  <div class="dashboard page-container">
    <!-- 管理员运营看板 -->
    <template v-if="isAdminView">
      <el-row :gutter="20" class="stats-cards">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #409EFF">
                <el-icon size="32"><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.today_borrows }}</div>
                <div class="stat-label">今日借阅</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #67C23A">
                <el-icon size="32"><Check /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.today_returns }}</div>
                <div class="stat-label">今日归还</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #E6A23C">
                <el-icon size="32"><Clock /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.total_overdue }}</div>
                <div class="stat-label">逾期未还</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #F56C6C">
                <el-icon size="32"><Money /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">¥{{ stats.today_fines }}</div>
                <div class="stat-label">今日罚款</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <el-row :gutter="20" class="charts-row">
        <el-col :span="16">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>借阅趋势</span>
                <el-radio-group v-model="trendDays" size="small" @change="loadBorrowTrend">
                  <el-radio-button :value="7">近7天</el-radio-button>
                  <el-radio-button :value="30">近30天</el-radio-button>
                  <el-radio-button :value="90">近90天</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <v-chart :option="trendOption" style="height: 350px" autoresize />
          </el-card>
        </el-col>
        
        <el-col :span="8">
          <el-card>
            <template #header>
              <span>分类分布</span>
            </template>
            <v-chart :option="categoryOption" style="height: 350px" autoresize />
          </el-card>
        </el-col>
      </el-row>
      
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>热门图书 TOP10</span>
            </template>
            <el-table :data="hotBooks" style="width: 100%" :show-header="false">
              <el-table-column prop="title" label="图书">
                <template #default="{ row, $index }">
                  <div class="book-item">
                    <span class="rank" :class="{ 'top3': $index < 3 }">{{ $index + 1 }}</span>
                    <div>
                      <div class="book-title">{{ row.title }}</div>
                      <div class="book-author">{{ row.author }}</div>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="borrow_count" label="借阅次数" width="100" align="right">
                <template #default="{ row }">
                  <el-tag type="primary">{{ row.borrow_count }} 次</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
        
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>系统概览</span>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="馆藏总数">
                <el-tag size="large">{{ stats.total_books }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="读者总数">
                <el-tag size="large" type="success">{{ stats.total_readers }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="当前借出">
                <el-tag size="large" type="warning">{{ stats.total_borrowed }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="预约等待">
                <el-tag size="large" type="info">{{ stats.total_reservations }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="图书流通率">
                <el-tag size="large" type="success">{{ stats.circulation_rate }}%</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="详细分析">
                <el-button size="small" type="primary" @click="$router.push('/statistics')">查看统计分析</el-button>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- 读者个人看板 -->
    <template v-else>
      <div class="reader-dashboard">
        <el-row :gutter="20" class="stats-cards">
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon" style="background: #409EFF">
                  <el-icon size="32"><Document /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ myStats.my_borrowing }}</div>
                  <div class="stat-label">在借图书</div>
                </div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon" style="background: #E6A23C">
                  <el-icon size="32"><Clock /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ myStats.my_overdue }}</div>
                  <div class="stat-label">逾期图书</div>
                </div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon" style="background: #67C23A">
                  <el-icon size="32"><Check /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ myStats.my_reservations }}</div>
                  <div class="stat-label">待处理预约</div>
                </div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon" style="background: #F56C6C">
                  <el-icon size="32"><Money /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">¥{{ myStats.my_fine_total }}</div>
                  <div class="stat-label">未缴罚款</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 当前借阅详情 -->
        <el-row :gutter="20" style="margin-top: 20px;">
          <el-col :span="24">
            <el-card v-loading="myBooksLoading">
              <template #header>
                <div class="card-header">
                  <span>我的在借图书</span>
                  <el-button type="primary" size="small" @click="$router.push('/borrows')">查看全部</el-button>
                </div>
              </template>
              <el-table :data="myBorrowList" border stripe v-if="myBorrowList.length > 0">
                <el-table-column prop="title" label="书名" min-width="180" show-overflow-tooltip />
                <el-table-column prop="author" label="作者" width="120" show-overflow-tooltip />
                <el-table-column label="到期日" width="120">
                  <template #default="{ row }">
                    <span :class="{ 'text-danger': row.is_overdue }">{{ row.due_date }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="90">
                  <template #default="{ row }">
                    <el-tag :type="row.is_overdue ? 'danger' : 'success'" size="small">
                      {{ row.is_overdue ? '已逾期' : '正常' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="renew_count" label="续借次数" width="80" align="center" />
              </el-table>
              <el-empty v-else description="暂无在借图书" :image-size="60" />
            </el-card>
          </el-col>

          <!-- 我的预约 -->
          <el-col :span="12" style="margin-top: 20px;">
            <el-card v-loading="myReservationsLoading">
              <template #header>
                <span>我的预约</span>
              </template>
              <el-table :data="myReservationList" border size="small" v-if="myReservationList.length > 0">
                <el-table-column prop="title" label="书名" min-width="140" show-overflow-tooltip />
                <el-table-column label="状态" width="90">
                  <template #default="{ row }">
                    <el-tag :type="row.status === 'ready' ? 'success' : 'warning'" size="small">
                      {{ row.status === 'ready' ? '可取书' : '排队中' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="70">
                  <template #default="{ row }">
                    <el-button link type="danger" size="small" @click="cancelMyReserve(row)">取消</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-empty v-else description="暂无预约记录" :image-size="50" />
            </el-card>
          </el-col>

          <!-- 借阅概况 -->
          <el-col :span="12" style="margin-top: 20px;">
            <el-card>
              <template #header><span>借阅概况</span></template>
              <el-descriptions :column="1" border>
                <el-descriptions-item label="历史借阅总数">
                  <el-tag>{{ myStats.my_total_borrows }} 本</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="未缴罚款笔数">
                  <el-tag type="warning">{{ myStats.my_unpaid_fines }} 笔</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="未缴罚款金额">
                  <el-tag type="danger">¥{{ myStats.my_fine_total }}</el-tag>
                </el-descriptions-item>
              </el-descriptions>
              <div style="margin-top: 16px; text-align: right;">
                <el-button type="primary" size="small" @click="$router.push('/fines')">查看罚款明细</el-button>
                <el-button size="small" @click="$router.push('/reservations')">查看预约管理</el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { Document, Check, Clock, Money } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent
])

const userStore = useUserStore()
const isAdminView = computed(() => ['super_admin', 'catalog_admin', 'circulation_admin', 'auditor'].includes(userStore.userRole))

const stats = reactive({
  today_borrows: 0,
  today_returns: 0,
  today_fines: 0,
  total_borrowed: 0,
  total_overdue: 0,
  total_reservations: 0,
  total_books: 0,
  total_copies: 0,
  total_readers: 0,
  circulation_rate: 0
})

const myStats = reactive({
  my_borrowing: 0,
  my_overdue: 0,
  my_reservations: 0,
  my_unpaid_fines: 0,
  my_fine_total: 0,
  my_total_borrows: 0
})

const trendDays = ref(30)
const hotBooks = ref([])

// 读者看板 - 借阅列表和预约列表
const myBorrowList = ref([])
const myReservationList = ref([])
const myBooksLoading = ref(false)
const myReservationsLoading = ref(false)

const trendOption = reactive({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  series: [{
    data: [],
    type: 'line',
    smooth: true,
    areaStyle: {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ]
      }
    },
    itemStyle: { color: '#409EFF' }
  }]
})

const categoryOption = reactive({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', left: 'left' },
  series: [{
    type: 'pie',
    radius: '60%',
    data: [],
    emphasis: {
      itemStyle: {
        shadowBlur: 10,
        shadowOffsetX: 0,
        shadowColor: 'rgba(0, 0, 0, 0.5)'
      }
    }
  }]
})

const loadDashboardStats = async () => {
  try {
    const res = await request.get('/statistics/dashboard')
    Object.assign(stats, res.data)
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

const loadMyDashboard = async () => {
  try {
    const res = await request.get('/statistics/my-dashboard')
    Object.assign(myStats, res.data)
  } catch (error) {
    console.error('加载个人统计数据失败:', error)
    ElMessage.warning('加载个人数据失败，请刷新重试')
  }
}

// 加载当前在借图书列表
const loadMyBorrows = async () => {
  myBooksLoading.value = true
  try {
    const res = await request.get('/borrows', { params: { page: 1, size: 50 } })
    const items = res.data?.items || []
    myBorrowList.value = items.map(b => ({
      title: b.title || '未知',
      author: b.author || '',
      due_date: b.due_date ? b.due_date.split('T')[0] : '--',
      is_overdue: b.is_overdue || false,
      renew_count: b.renew_count || 0,
      borrow_id: b.borrow_id,
    }))
  } catch (error) {
    console.error('加载借阅列表失败:', error)
  } finally {
    myBooksLoading.value = false
  }
}

// 加载我的预约列表
const loadMyReservations = async () => {
  myReservationsLoading.value = true
  try {
    const res = await request.get('/reservations', { params: { page: 1, size: 20 } })
    myReservationList.value = (res.data?.items || []).map(r => ({
      title: r.title || '未知',
      status: r.status,
      reservation_id: r.reservation_id,
    }))
  } catch (error) {
    console.error('加载预约列表失败:', error)
  } finally {
    myReservationsLoading.value = false
  }
}

// 取消预约（读者看板内）
const cancelMyReserve = async (row) => {
  try {
    await ElMessageBox.confirm(`确定取消《${row.title}》的预约吗？`, '取消预约', { type: 'warning' })
    await request.post(`/reservations/${row.reservation_id}/cancel`)
    ElMessage.success('已取消')
    loadMyReservations()
    loadMyDashboard()
  } catch (e) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || '操作失败')
    }
  }
}

const loadBorrowTrend = async () => {
  try {
    const res = await request.get('/statistics/borrow-trend', {
      params: { days: trendDays.value }
    })
    
    const data = res.data
    trendOption.xAxis.data = data.map(item => item.date)
    trendOption.series[0].data = data.map(item => item.count)
  } catch (error) {
    console.error('加载借阅趋势失败:', error)
  }
}

const loadCategoryDistribution = async () => {
  try {
    const res = await request.get('/statistics/category-distribution')
    const data = res.data
    
    categoryOption.series[0].data = data.map(item => ({
      name: item.category_name,
      value: item.book_count
    }))
  } catch (error) {
    console.error('加载分类分布失败:', error)
  }
}

const loadHotBooks = async () => {
  try {
    const res = await request.get('/statistics/hot-books', {
      params: { limit: 10 }
    })
    hotBooks.value = res.data
  } catch (error) {
    console.error('加载热门图书失败:', error)
  }
}

onMounted(() => {
  if (isAdminView.value) {
    loadDashboardStats()
    loadBorrowTrend()
    loadCategoryDistribution()
    loadHotBooks()
  } else {
    loadMyDashboard()
    loadMyBorrows()
    loadMyReservations()
  }
})
</script>

<style scoped lang="scss">
.stats-cards {
  margin-bottom: 20px;
}

.stat-card {
  .stat-content {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  
  .stat-icon {
    width: 64px;
    height: 64px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
  }
  
  .stat-info {
    flex: 1;
  }
  
  .stat-value {
    font-size: 28px;
    font-weight: bold;
    color: #303133;
    margin-bottom: 4px;
  }
  
  .stat-label {
    font-size: 14px;
    color: #909399;
  }
}

.charts-row {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.book-item {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .rank {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #f0f0f0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 14px;
    
    &.top3 {
      background: #409EFF;
      color: #fff;
    }
  }
  
  .book-title {
    font-size: 14px;
    color: #303133;
    margin-bottom: 4px;
  }
  
  .book-author {
    font-size: 12px;
    color: #909399;
  }
}

.text-danger {
  color: #F56C6C;
  font-weight: 500;
}
</style>
