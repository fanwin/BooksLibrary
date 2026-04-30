<template>
  <div class="dashboard page-container">
    <!-- 管理员运营看板 -->
    <template v-if="isAdminView">
      <el-row :gutter="20" class="stats-cards">
        <!-- ===== 当日核心指标 (4张) ===== -->
        <el-col :xs="12" :sm="12" :md="6" :lg="4">
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

        <el-col :xs="12" :sm="12" :md="6" :lg="4">
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

        <el-col :xs="12" :sm="12" :md="6" :lg="4">
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

        <el-col :xs="12" :sm="12" :md="6" :lg="4">
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

        <!-- ===== 累计 & 周期指标 (4张) ===== -->
        <el-col :xs="24" :sm="12" :md="12" :lg="4">
          <el-card shadow="hover" class="stat-card stat-card-highlight">
            <div class="stat-content">
              <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
                <el-icon size="32"><Reading /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.total_borrow_count.toLocaleString() }}</div>
                <div class="stat-label">总借阅次数</div>
                <div class="stat-sublabel">累计历史全部借阅记录</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="12" :md="12" :lg="4">
          <el-card shadow="hover" class="stat-card stat-card-fine">
            <div class="stat-content">
              <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%)">
                <el-icon size="32"><Wallet /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">¥{{ stats.total_fines_amount.toLocaleString() }}</div>
                <div class="stat-label">罚款总数</div>
                <div class="stat-sublabel">累计历史全部已缴罚款</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- === Phase2: 本周借阅 + 环比增长 === -->
        <el-col :xs="24" :sm="12" :md="8" :lg="4">
          <el-card shadow="hover" class="stat-card stat-card-week">
            <div class="stat-content">
              <div class="stat-icon" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)">
                <el-icon size="28"><TrendCharts /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">
                  {{ stats.week_borrows }}
                  <span v-if="stats.week_growth !== 0"
                        :class="stats.week_growth > 0 ? 'trend-up' : 'trend-down'"
                        class="trend-badge">
                    {{ stats.week_growth > 0 ? '↑' : '↓' }}{{ Math.abs(stats.week_growth) }}%
                  </span>
                </div>
                <div class="stat-label">本周借阅</div>
                <div class="stat-sublabel">周环比 {{ stats.week_growth >= 0 ? '+' : '' }}{{ stats.week_growth }}%</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- === Phase2: 未缴罚款总额 === -->
        <el-col :xs="24" :sm="12" :md="8" :lg="4">
          <el-card shadow="hover" class="stat-card stat-card-unpaid">
            <div class="stat-content">
              <div class="stat-icon" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%)">
                <el-icon size="28"><Warning /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">¥{{ stats.unpaid_fines_total.toLocaleString() }}</div>
                <div class="stat-label">未缴罚款</div>
                <div class="stat-sublabel">待收金额（财务视角）</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- ===== Phase2 第二行：周期 & 健康 & 用户指标 ===== -->
      <el-row :gutter="20" class="stats-cards">
        <!-- 本月借阅 + 月环比 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-card shadow="hover" class="stat-card stat-card-month">
            <div class="stat-content">
              <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)">
                <el-icon size="28"><DataAnalysis /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">
                  {{ stats.month_borrows }}
                  <span v-if="stats.month_growth !== 0"
                        :class="stats.month_growth > 0 ? 'trend-up' : 'trend-down'"
                        class="trend-badge">
                    {{ stats.month_growth > 0 ? '↑' : '↓' }}{{ Math.abs(stats.month_growth) }}%
                  </span>
                </div>
                <div class="stat-label">本月借阅</div>
                <div class="stat-sublabel">月环比 {{ stats.month_growth >= 0 ? '+' : '' }}{{ stats.month_growth }}%</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 今日新注册用户 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-card shadow="hover" class="stat-card stat-card-newuser">
            <div class="stat-content">
              <div class="stat-icon" style="background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)">
                <el-icon size="28"><User /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.today_new_readers }}</div>
                <div class="stat-label">今日新读者</div>
                <div class="stat-sublabel">新增注册人数</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 馆藏健康度 — 在馆率 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-card shadow="hover" class="stat-card stat-card-health">
            <div class="stat-content">
              <div class="stat-icon" style="background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)">
                <el-icon size="28"><DataAnalysis /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.available_rate }}%</div>
                <div class="stat-label">在馆率</div>
                <div class="stat-sublabel">可借 / 总馆藏副本</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 沉睡图书数量 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-card shadow="hover" class="stat-card stat-card-dormant">
            <div class="stat-content">
              <div class="stat-icon" style="background: linear-gradient(135deg, #c0c3c9 0%, #a6a8ad 100%)">
                <el-icon size="28"><Reading /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.dormant_books_count.toLocaleString() }}</div>
                <div class="stat-label">沉睡图书</div>
                <div class="stat-sublabel">180天未被借阅</div>
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

      <!-- ===== Phase1 第三行：活跃读者 + 待处理预警 + 热门图书 ===== -->
      <el-row :gutter="20">
        <!-- 活跃读者 TOP5 -->
        <el-col :span="8">
          <el-card>
            <template #header>
              <span>🏆 活跃读者 TOP5（近30天）</span>
            </template>
            <div v-if="activeReaders.length" class="reader-rank-list">
              <div v-for="(r, i) in activeReaders" :key="r.user_id" class="rank-item">
                <span class="rank-num" :class="{ 'top3': i < 3 }">{{ i + 1 }}</span>
                <span class="rank-name">{{ r.username }}</span>
                <div style="flex:1; margin-left:12px;">
                  <div class="rank-bar-wrap">
                    <div class="rank-bar"
                         :style="{ width: (r.borrow_count / (activeReaders[0]?.borrow_count || 1) * 100) + '%' }">
                    </div>
                  </div>
                </div>
                <span class="rank-count"><strong>{{ r.borrow_count }}</strong>次</span>
              </div>
            </div>
            <el-empty v-else description="暂无数据" :image-size="50" />
          </el-card>
        </el-col>

        <!-- 待处理预警面板 -->
        <el-col :span="8">
          <el-card v-loading="alertLoading">
            <template #header>
              <span>⚠️ 待处理预警</span>
            </template>
            <div v-if="overdueAlerts.length" class="alert-list">
              <div v-for="(a, i) in overdueAlerts" :key="i" class="alert-item" :class="'alert-' + a.type">
                <div class="alert-title">{{ a.title }}</div>
                <div class="alert-subtitle">{{ a.subtitle }}</div>
                <div class="alert-detail">{{ a.detail }}</div>
              </div>
            </div>
            <el-empty v-else description="暂无预警项，一切正常 ✨" :image-size="50" />
          </el-card>
        </el-col>

        <!-- 热门图书 TOP10 -->
        <el-col :span="8">
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
              <el-descriptions-item label="在馆率">
                <el-tag size="large">{{ stats.available_rate }}%</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="未缴罚款">
                <el-tag size="large" type="danger">¥{{ stats.unpaid_fines_total }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="沉睡图书">
                <el-tag size="large" type="info">{{ stats.dormant_books_count }} 本</el-tag>
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
import { Document, Check, Clock, Money, Reading, Wallet, TrendCharts, Warning, User, DataAnalysis } from '@element-plus/icons-vue'
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
  // --- 当日核心 ---
  today_borrows: 0,
  today_returns: 0,
  today_fines: 0,
  total_borrowed: 0,
  total_overdue: 0,
  total_reservations: 0,
  total_books: 0,
  total_copies: 0,
  total_readers: 0,

  // --- 累计指标 ---
  total_borrow_count: 0,
  total_fines_amount: 0,
  circulation_rate: 0,

  // === Phase2: 周期统计 + 环比 ===
  week_borrows: 0,
  month_borrows: 0,
  week_growth: 0,        // 周环比 %
  month_growth: 0,       // 月环比 %

  // === Phase2: 财务 & 用户 ===
  unpaid_fines_total: 0,   // 未缴罚款总额
  today_new_readers: 0,    // 今日新注册用户

  // === Phase1: 馆藏健康度 & 活跃读者 & 待处理预警 ===
  available_rate: 0,       // 在馆率 %
  dormant_books_count: 0,  // 沉睡图书本数
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

// === Phase1: 活跃读者 TOP5 & 待处理预警 ===
const activeReaders = ref([])
const overdueAlerts = ref([])  // 精简版预警列表（前5条）
const alertLoading = ref(false)

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

// === Phase1: 活跃读者 TOP5 ===
const loadActiveReaders = async () => {
  try {
    const res = await request.get('/statistics/active-readers', { params: { days: 30, limit: 5 } })
    activeReaders.value = res.data
  } catch (error) {
    console.error('加载活跃读者失败:', error)
  }
}

// === Phase1: 待处理预警（合并超期未还 + 高频逾期读者）===
const loadAlerts = async () => {
  alertLoading.value = true
  try {
    // 并发获取超期报告和逾期读者
    const [overdueRes, readersRes] = await Promise.allSettled([
      request.get('/statistics/overdue-report'),
      request.get('/statistics/overdue-readers', { params: { limit: 3 } }),
    ])
    const overdueList = overdueRes.status === 'fulfilled' ? (overdueRes.value.data || []) : []
    const readerList = readersRes.status === 'fulfilled' ? (readersRes.value.data || []) : []
    // 取超期前3 + 高频逾期读者前2，组合成预警摘要
    overdueAlerts.value = [
      ...(overdueList.slice(0, 3).map(item => ({
        type: 'overdue_book',
        title: item.book_title,
        subtitle: item.username,
        detail: `逾期 ${item.overdue_days} 天`,
      }))),
      ...readerList.slice(0, 2).map(item => ({
        type: 'overdue_reader',
        title: item.username,
        subtitle: `逾期 ${item.overdue_count} 本`,
        detail: `最高 ${item.max_overdue_days} 天`,
      })),
    ]
  } catch (error) {
    console.error('加载待处理预警失败:', error)
  } finally {
    alertLoading.value = false
  }
}

onMounted(() => {
  if (isAdminView.value) {
    loadDashboardStats()
    loadBorrowTrend()
    loadCategoryDistribution()
    loadHotBooks()
    // Phase1 新增
    loadActiveReaders()
    loadAlerts()
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

// ⭐ 总借阅数量高亮卡片样式
.stat-card-highlight {
  background: linear-gradient(135deg, #f0f4ff 0%, #e8ecff 100%);
  border: 1px solid #c7d2fe;

  .stat-icon {
    width: 64px;
    height: 64px;
    border-radius: 14px;
  }

  .stat-sublabel {
    font-size: 12px;
    color: #8b95a5;
    margin-top: 2px;
  }
}

// ⭐ 罚款总数卡片样式
.stat-card-fine {
  background: linear-gradient(135deg, #fff0f3 0%, #ffe4e8 100%);
  border: 1px solid #fecdd3;

  .stat-icon {
    width: 64px;
    height: 64px;
    border-radius: 14px;
  }

  .stat-sublabel {
    font-size: 12px;
    color: #8b95a5;
    margin-top: 2px;
  }
}

// === Phase2: 本周借阅 + 环比 ===
.stat-card-week {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border: 1px solid #bbf7d0;

  .stat-icon { width: 56px; height: 56px; border-radius: 14px; }
  .stat-sublabel { font-size: 12px; color: #8b95a5; margin-top: 2px; }
}

// === Phase2: 未缴罚款 ===
.stat-card-unpaid {
  background: linear-gradient(135deg, #fefce8 0%, #fef08a 100%);
  border: 1px solid #fde047;

  .stat-icon { width: 56px; height: 56px; border-radius: 14px; }
  .stat-sublabel { font-size: 12px; color: #8b95a5; margin-top: 2px; }
}

// === Phase2: 本月借阅 ===
.stat-card-month {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #bae6fd;

  .stat-icon { width: 56px; height: 56px; border-radius: 14px; }
  .stat-sublabel { font-size: 12px; color: #8b95a5; margin-top: 2px; }
}

// === Phase2: 今日新读者 ===
.stat-card-newuser {
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border: 1px solid #d8b4fe;

  .stat-icon { width: 56px; height: 56px; border-radius: 14px; }
  .stat-sublabel { font-size: 12px; color: #8b95a5; margin-top: 2px; }
}

// === Phase1: 在馆率（馆藏健康）===
.stat-card-health {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border: 1px solid #a7f3d0;

  .stat-icon { width: 56px; height: 56px; border-radius: 14px; }
  .stat-sublabel { font-size: 12px; color: #8b95a5; margin-top: 2px; }
}

// === Phase1: 沉睡图书 ===
.stat-card-dormant {
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border: 1px solid #d1d5db;

  .stat-icon { width: 56px; height: 56px; border-radius: 14px; }
  .stat-sublabel { font-size: 12px; color: #8b95a5; margin-top: 2px; }
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

// === 环比趋势徽章 ===
.trend-badge {
  font-size: 12px;
  font-weight: 600;
  margin-left: 4px;
}
.trend-up { color: #67C23A; }
.trend-down { color: #F56C6C; }

// === Phase1: 活跃读者排行条形图 ===
.reader-rank-list {
  .rank-item {
    display: flex;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;

    &:last-child { border-bottom: none; }
  }
  .rank-num {
    width: 24px; height: 24px; border-radius: 50%;
    background: #f0f0f0; display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: bold; color: #909399; margin-right: 10px;
    &.top3 { background: #409EFF; color: #fff; }
  }
  .rank-name { width: 70px; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rank-bar-wrap {
    height: 8px; border-radius: 4px; background: #ecf5ff; overflow: hidden;
  }
  .rank-bar {
    height: 100%; border-radius: 4px; background: linear-gradient(90deg, #409EFF, #79bbff); transition: width 0.6s ease;
  }
  .rank-count { font-size: 12px; color: #606266; min-width: 48px; text-align: right; }
}

// === Phase1: 待处理预警列表 ===
.alert-list {
  .alert-item {
    padding: 10px 12px; margin-bottom: 8px; border-radius: 8px;
    border-left: 3px solid #E6A23C;
    background: #fffbeb;

    &.alert-overdue_reader { border-left-color: #F56C6C; background: #fef2f2; }
  }
  .alert-title { font-size: 14px; font-weight: 600; color: #303133; }
  .alert-subtitle { font-size: 12px; color: #909399; margin-top: 2px; }
  .alert-detail { font-size: 12px; color: #E6A23C; margin-top: 4px; }
}
</style>
