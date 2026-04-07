<template>
  <div class="statistics page-container">
    <!-- 顶部工具栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <span class="title">数据统计分析</span>
        <div class="toolbar-actions">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            :shortcuts="dateShortcuts"
            value-format="YYYY-MM-DD"
            style="width: 260px"
          />
          <el-select v-model="exportType" placeholder="导出报表" style="width: 140px" @change="handleExport">
            <el-option label="月度流通报表" value="monthly" />
            <el-option label="年度采购分析" value="yearly" />
            <el-option label="自定义范围报表" value="custom" />
          </el-select>
        </div>
      </div>
    </el-card>

    <!-- 借阅统计区域 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 热门图书排行 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>热门图书 TOP10</span></template>
          <el-table :data="hotBooks" size="small" :show-header="false">
            <el-table-column width="60">
              <template #default="{ $index }">
                <span class="rank" :class="{ top3: $index < 3 }">{{ $index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="图书" min-width="180">
              <template #default="{ row }">
                <div class="book-item"><b>{{ row.title }}</b><span class="author">{{ row.author }}</span></div>
              </template>
            </el-table-column>
            <el-table-column prop="borrow_count" width="90" align="right">
              <template #default="{ row }"><el-tag size="small" type="primary">{{ row.borrow_count }}次</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 活跃读者排行 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>活跃读者排行</span></template>
          <el-table :data="activeReaders" size="small" :show-header="false">
            <el-table-column width="50"><template #default="{ $index }"><span class="rank-sm">{{$index+1}}</span></template></el-table-column>
            <el-table-column prop="username" label="用户名" min-width="100" />
            <el-table-column prop="borrow_count" width="100" align="right">
              <template #default="{ row }"><el-tag size="small" type="success">{{ row.borrow_count }}次</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>借阅趋势</span>
              <el-radio-group v-model="trendDays" size="small" @change="loadTrend">
                <el-radio-button :label="7">近7天</el-radio-button>
                <el-radio-button :label="30">近30天</el-radio-button>
                <el-radio-button :label="90">近90天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart :option="trendOption" style="height: 320px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>分类借阅分布</span></template>
          <v-chart :option="categoryOption" style="height: 320px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 异常报告区域 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>超期未还清单</span></template>
          <el-table :data="overdueList" size="small" max-height="300">
            <el-table-column prop="username" label="读者" width="90" />
            <el-table-column prop="book_title" label="图书" min-width="150" show-overflow-tooltip />
            <el-table-column prop="overdue_days" label="逾期天数" width="85" align="center">
              <template #default="{ row }"><el-tag size="small" type="danger">{{ row.overdue_days }}天</el-tag></template>
            </el-table-column>
            <el-table-column prop="fine_amount" label="预估罚金" width="80" align="right">
              <template #default="{ row }">¥{{ row.fine_amount?.toFixed(1) || '0.0' }}</template>
            </el-table-column>
          </el-table>
          <div v-if="overdueList.length === 0" style="padding: 20px; text-align: center; color: #999;">暂无超期记录</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>高频逾期读者</span></template>
          <el-table :data="overdueReaders" size="small" max-height="300" :show-header="false">
            <el-table-column min-width="120">
              <template #default="{ row }">
                <div><b>{{ row.username }}</b></div>
                <div class="sub-text">逾期 {{ row.overdue_count }} 本 · 最高 {{ row.max_overdue_days }} 天</div>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="overdueReaders.length === 0" style="padding: 15px; text-align: center; color: #67C23A;">暂无逾期读者</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>沉睡图书 ({{ dormantBooks.length }}本)</span></template>
          <el-table :data="dormantBooks.slice(0, 8)" size="small" :show-header="false" max-height="300">
            <el-table-column prop="title" min-width="140" show-overflow-tooltip>
              <template #default="{ row }"><span class="dormant-title">{{ row.title }}</span></template>
            </el-table-column>
          </el-table>
          <div v-if="dormantBooks.length === 0" style="padding: 15px; text-align: center; color: #67C23A;">无沉睡图书</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 流通率统计 -->
    <el-card shadow="hover" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>馆藏流通率分析</span>
          <el-tag type="info">整体流通率: {{ circRate.overall_rate }}%</el-tag>
        </div>
      </template>
      <el-descriptions :column="4" border size="small" style="margin-bottom: 16px;">
        <el-descriptions-item label="总图书数">{{ circRate.total_books }}</el-descriptions-item>
        <el-descriptions-item label="总副本数">{{ circRate.total_copies }}</el-descriptions-item>
        <el-descriptions-item label="当前借出">{{ circRate.currently_borrowed }}</el-descriptions-item>
        <el-descriptions-item label="历史总借阅">{{ circRate.total_borrow_history }}</el-descriptions-item>
      </el-descriptions>
      <v-chart :option="circulationOption" style="height: 250px" autoresize />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import request from '@/utils/request'

use([CanvasRenderer, BarChart, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

// 数据
const hotBooks = ref([])
const activeReaders = ref([])
const overdueList = ref([])
const overdueReaders = ref([])
const dormantBooks = ref([])
const trendDays = ref(30)
const dateRange = ref(null)
const exportType = ref('')

const circRate = reactive({ overall_rate: 0, total_books: 0, total_copies: 0, currently_borrowed: 0, total_borrow_history: 0 })

// 图表配置
const trendOption = reactive({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: [], boundaryGap: false },
  yAxis: { type: 'value', name: '借阅量' },
  series: [{ data: [], type: 'line', smooth: true, areaStyle: {
    color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
      colorStops: [{ offset: 0, color: 'rgba(64,158,255,0.3)' }, { offset: 1, color: 'rgba(64,158,255,0.05)' }] }
  }, itemStyle: { color: '#409EFF' } }]
})

const categoryOption = reactive({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { orient: 'vertical', left: 'left', top: 'middle' },
  series: [{ type: 'pie', radius: ['35%', '65%'], center: ['55%', '50%'], data: [],
    emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
    label: { fontSize: 11, formatter: '{b}\n{d}%' }
  }]
})

const circulationOption = reactive({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: [], axisLabel: { rotate: 30, fontSize: 11 } },
  yAxis: { type: 'value', name: '流通率(%)', min: 0 },
  grid: { left: '3%', right: '8%', bottom: '18%', containLabel: true },
  series: [{
    type: 'bar', barMaxWidth: 40,
    itemStyle: { borderRadius: [4, 4, 0, 0], color: new (function () {
      const c = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de']
      return { getColor: (p) => c[p.dataIndex % c.length] }
    })() },
    data: []
  }]
})

// 快捷日期
const dateShortcuts = [
  { text: '最近一周', value: () => { const e = new Date(), s = new Date(); s.setDate(s.getDate() - 7); return [s, e] } },
  { text: '最近一月', value: () => { const e = new Date(), s = new Date(); s.setMonth(s.getMonth() - 1); return [s, e] } },
  { text: '最近三月', value: () => { const e = new Date(), s = new Date(); s.setMonth(s.getMonth() - 3); return [s, e] } },
]

// 加载函数
async function loadHotBooks() {
  try {
    const res = await request.get('/statistics/hot-books', { params: { days: 30, limit: 10 } })
    hotBooks.value = res.data || []
  } catch (e) {}
}

async function loadActiveReaders() {
  try {
    const res = await request.get('/statistics/active-readers', { params: { days: 30, limit: 10 } })
    activeReaders.value = res.data || []
  } catch (e) {}
}

async function loadTrend() {
  try {
    const res = await request.get('/statistics/borrow-trend', { params: { days: trendDays.value } })
    const d = res.data || []
    trendOption.xAxis.data = d.map(i => i.date)
    trendOption.series[0].data = d.map(i => i.count)
  } catch (e) {}
}

async function loadCategoryDist() {
  try {
    const res = await request.get('/statistics/category-distribution')
    const d = res.data || []
    categoryOption.series[0].data = d.map(i => ({ name: i.category_name, value: i.borrow_count }))
  } catch (e) {}
}

async function loadOverdueReport() {
  try {
    const res = await request.get('/statistics/overdue-report')
    overdueList.value = res.data || []
  } catch (e) {}
}

async function loadOverdueReaders() {
  try {
    const res = await request.get('/statistics/overdue-readers', { params: { limit: 10 } })
    overdueReaders.value = res.data || []
  } catch (e) {}
}

async function loadDormantBooks() {
  try {
    const res = await request.get('/statistics/dormant-books', { params: { days: 180 } })
    dormantBooks.value = res.data?.books || []
  } catch (e) {}
}

async function loadCirculationRate() {
  try {
    const res = await request.get('/statistics/circulation-rate')
    const d = res.data || {}
    Object.assign(circRate, d)
    if (d.categories) {
      circulationOption.xAxis.data = d.categories.map(c => c.category_name)
      circulationOption.series[0].data = d.categories.map(c => c.circulation_rate)
    }
  } catch (e) {}
}

async function handleExport(type) {
  if (!type) return
  exportType.value = ''
  try {
    let url = '/api/v1/statistics/export/borrow-report?report_type=' + type
    if (type === 'custom' && dateRange.value && dateRange.value.length === 2) {
      url += `&start_date=${dateRange.value[0]}T00:00:00&end_date=${dateRange.value[1]}T23:59:59`
    }
    const token = localStorage.getItem('access_token')
    const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    if (!resp.ok) throw Error('导出失败')
    const blob = await resp.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `library_report_${type}_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
    ElMessage.success('报表导出成功')
  } catch (e) { ElMessage.error('导出失败') }
}

onMounted(() => {
  loadHotBooks()
  loadActiveReaders()
  loadTrend()
  loadCategoryDist()
  loadOverdueReport()
  loadOverdueReaders()
  loadDormantBooks()
  loadCirculationRate()
})
</script>

<style scoped lang="scss">
.toolbar-card .toolbar { display: flex; justify-content: space-between; align-items: center; }
.toolbar .title { font-size: 18px; font-weight: 600; color: #303133; }
.toolbar-actions { display: flex; gap: 12px; align-items: center; }

.card-header { display: flex; justify-content: space-between; align-items: center; }
.rank { display: inline-flex; width: 24px; height: 24px; border-radius: 50%; background: #f0f0f0; align-items: center; justify-content: center; font-weight: bold; font-size: 12px; color: #666; &.top3 { background: #409EFF; color: #fff; } }
.rank-sm { font-size: 11px; color: #999; font-weight: bold; }
.book-item { .book-title { font-size: 13px; } .author { font-size: 11px; color: #909399; margin-top: 2px; } }
.sub-text { font-size: 11px; color: #E6A23C; margin-top: 2px; }
.dormant-title { color: #909399; font-size: 12px; }
</style>
