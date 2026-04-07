<template>
  <div class="borrow-list page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>借阅流通管理</span>
          <el-button v-if="canBorrow" type="primary" @click="showBorrowDialog = true">
            <el-icon><Plus /></el-icon> 借书
          </el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-form :inline="true" :model="filterForm">
          <el-form-item label="读者">
            <el-input v-model="filterForm.keyword" placeholder="读者名/书名" clearable @clear="fetchData" @keyup.enter="fetchData" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filterForm.status" placeholder="全部" clearable @change="fetchData">
              <el-option label="借阅中" value="active" />
              <el-option label="已归还" value="returned" />
              <el-option label="逾期" value="overdue" />
              <el-option label="丢失" value="lost" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchData">查询</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="borrow_id" label="ID" width="70" />
        <el-table-column prop="username" label="读者" width="100" />
        <el-table-column prop="title" label="图书" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.title }}
            <span class="text-muted">({{ row.author }})</span>
          </template>
        </el-table-column>
        <el-table-column prop="barcode" label="条码号" width="150" show-overflow-tooltip />
        <el-table-column prop="borrow_date" label="借阅日期" width="110" sortable />
        <el-table-column prop="due_date" label="应还日期" width="110" sortable>
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.is_overdue }">{{ row.due_date }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="return_date" label="归还日期" width="110" />
        <el-table-column prop="return_branch" label="归还分馆" width="100">
          <template #default="{ row }">
            <span v-if="row.return_branch" class="branch-tag">
              <el-icon size="12"><OfficeBuilding /></el-icon> {{ row.return_branch }}
            </span>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column prop="status_text" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="renew_count" label="续借" width="60" align="center" />
        <el-table-column prop="fine_amount" label="罚款(￥)" width="85" align="right">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.fine_amount > 0 }">{{ row.fine_amount.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
            <el-button
              v-if="row.status === 'active' && !row.is_overdue"
              link type="warning"
              size="small"
              @click="handleRenew(row)"
            >续借</el-button>
            <el-button
              v-if="row.status === 'active'"
              link type="success"
              size="small"
              @click="handleReturn(row)"
            >还书</el-button>
            <el-tag v-if="row.is_overdue && row.status === 'active'" type="danger" size="small" effect="dark">
              逾期{{ row.overdue_days }}天
            </el-tag>
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

    <!-- 借书对话框 -->
    <el-dialog v-model="showBorrowDialog" title="借书操作" width="640px" :close-on-click-modal="false" @close="resetBorrowForm">
      <!-- 第一步：查询读者 -->
      <el-form :model="borrowForm" :rules="borrowRules" ref="borrowRef" label-width="100px">
        <el-form-item label="读者ID" prop="user_id">
          <div style="display:flex;gap:8px;width:100%">
            <el-input-number v-model="borrowForm.user_id" :min="1" placeholder="输入读者ID" style="flex:1" :disabled="!!readerInfo" />
            <el-button type="primary" :loading="readerLoading" :disabled="!!readerInfo" @click="lookupReader">
              查询读者
            </el-button>
            <el-button v-if="readerInfo" @click="clearReader">清除</el-button>
          </div>
        </el-form-item>
      </el-form>

      <!-- 读者信息卡片 -->
      <div v-if="readerInfo" class="reader-info-card">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="读者">{{ readerInfo.username }}</el-descriptions-item>
          <el-descriptions-item label="证号">{{ readerInfo.reader_card_number || '--' }}</el-descriptions-item>
          <el-descriptions-item label="读者类型">{{ readerInfo.reader_type || '--' }}</el-descriptions-item>
          <el-descriptions-item label="账户状态">
            <el-tag :type="readerInfo.status === 'active' ? 'success' : 'danger'" size="small">
              {{ readerInfo.status === 'active' ? '正常' : '异常' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最大借阅">{{ readerInfo.max_borrow_count }} 本</el-descriptions-item>
          <el-descriptions-item label="借阅期限">{{ readerInfo.borrow_limit_days }} 天</el-descriptions-item>
        </el-descriptions>

        <!-- 资格检查结果 -->
        <div class="eligibility-result" v-if="eligibilityChecked">
          <el-alert v-if="eligibilityResult.eligible" type="success" :closable="false" show-icon title="借阅资格正常，可以借书" />
          <el-alert v-else type="error" :closable="false" show-icon :title="eligibilityResult.reason" />
        </div>
      </div>

      <el-divider v-if="readerInfo && eligibilityResult?.eligible" />

      <!-- 第二步：添加副本（两种方式） -->
      <div v-if="readerInfo && eligibilityResult?.eligible" class="copy-input-section">
        <!-- 方式切换 -->
        <div class="add-mode-switch">
          <el-radio-group v-model="addMode" size="small">
            <el-radio-button value="barcode">扫码/条码</el-radio-button>
            <el-radio-button value="search">搜索图书</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 方式一：扫码输入条码 -->
        <div v-if="addMode === 'barcode'">
          <el-form label-width="100px">
            <el-form-item label="扫描条码">
              <div class="copy-input-area">
                <el-input
                  v-model="copyBarcodeInput"
                  placeholder="扫描或输入图书条码后按回车添加"
                  @keyup.enter="addCopyByBarcode"
                  clearable
                >
                  <template #append>
                    <el-button @click="addCopyByBarcode">添加</el-button>
                  </template>
                </el-input>
              </div>
            </el-form-item>
          </el-form>
        </div>

        <!-- 方式二：搜索图书选副本 -->
        <div v-if="addMode === 'search'">
          <el-form label-width="100px">
            <el-form-item label="搜索图书">
              <div style="display:flex;gap:8px;width:100%">
                <el-input
                  v-model="bookSearchKeyword"
                  placeholder="输入书名、作者或ISBN搜索"
                  @keyup.enter="searchBooks"
                  clearable
                >
                  <template #append>
                    <el-button @click="searchBooks">搜索</el-button>
                  </template>
                </el-input>
              </div>
            </el-form-item>
          </el-form>
          <!-- 搜索结果 -->
          <div v-if="bookSearchResults.length > 0" class="book-search-results">
            <div class="section-title">找到 {{ bookSearchResults.length }} 本图书</div>
            <el-table :data="bookSearchResults" border size="small" max-height="200">
              <el-table-column prop="title" label="书名" min-width="150" show-overflow-tooltip />
              <el-table-column prop="author" label="作者" width="100" show-overflow-tooltip />
              <el-table-column prop="isbn" label="ISBN" width="130" show-overflow-tooltip />
              <el-table-column label="可借" width="60" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.available_copies > 0 ? 'success' : 'info'" size="small">
                    {{ row.available_copies }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" align="center">
                <template #default="{ row }">
                  <el-button
                    link type="primary" size="small"
                    :disabled="row.available_copies <= 0"
                    :loading="addingBookId === row.book_id"
                    @click="addBookDirectly(row)"
                  >借阅</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 已选副本列表 -->
        <div v-if="selectedCopies.length > 0" class="selected-copies-section">
          <div class="section-title">
            已选 {{ selectedCopies.length }} 本图书
            <el-button link type="danger" size="small" @click="clearAllCopies">清空</el-button>
          </div>
          <el-table :data="selectedCopies" border size="small" max-height="200">
            <el-table-column prop="title" label="书名" min-width="160" show-overflow-tooltip />
            <el-table-column prop="barcode" label="条码" width="160" show-overflow-tooltip />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'available' ? 'success' : 'info'" size="small">
                  {{ row.status === 'available' ? '可借' : row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" align="center">
              <template #default="{ $index }">
                <el-button link type="danger" size="small" @click="removeCopy($index)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

    <!-- 选择副本子对话框 -->
    <el-dialog v-model="showCopySelectorDialog" title="选择可借副本" width="500px" append-to-body>
      <div v-if="copySelectorBook">
        <p style="margin-bottom:12px"><strong>{{ copySelectorBook.title }}</strong>
          <span class="text-muted" v-if="copySelectorBook.author"> - {{ copySelectorBook.author }}</span></p>
        <el-table :data="availableCopies" border size="small" v-loading="copyListLoading">
          <el-table-column prop="barcode" label="条码" width="170" />
          <el-table-column prop="location_detail" label="位置" width="120">
            <template #default="{ row }">{{ row.location_detail || '--' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="addCopyFromSelector(row)">添加</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!copyListLoading && availableCopies.length === 0" description="没有可借的副本" />
      </div>
    </el-dialog>

      <template #footer>
        <el-button @click="showBorrowDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="borrowLoading"
          :disabled="!canSubmitBorrow"
          @click="submitBorrow"
        >确认借书 ({{ selectedCopies.length }}本)</el-button>
      </template>
    </el-dialog>

    <!-- 续借确认对话框 -->
    <el-dialog v-model="showRenewDialog" title="续借确认" width="400px">
      <div v-if="renewInfo">
        <p><strong>图书：</strong>{{ renewInfo.title }}</p>
        <p><strong>当前应还：</strong>{{ renewInfo.due_date }}</p>
        <p><strong>已续借：</strong>{{ renewInfo.renew_count }} / {{ renewInfo.max_renew_count || 2 }} 次</p>
        <p><strong>可延长：</strong>{{ renewInfo.renew_days || 15 }} 天</p>
        <el-alert v-if="renewInfo.renew_count >= (renewInfo.max_renew_count || 2)" type="error" :closable="false" show-icon>
          已达最大续借次数！
        </el-alert>
      </div>
      <template #footer>
        <el-button @click="showRenewDialog = false">取消</el-button>
        <el-button type="primary" :loading="renewLoading" @click="confirmRenew">确认续借</el-button>
      </template>
    </el-dialog>

    <!-- 还书对话框 -->
    <el-dialog v-model="showReturnDialog" title="还书确认" width="480px">
      <div v-if="returnInfo">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="图书">{{ returnInfo.title }}</el-descriptions-item>
          <el-descriptions-item label="应还日期">{{ returnInfo.due_date }}</el-descriptions-item>
          <el-descriptions-item label="当前日期">{{ returnInfo.return_date }}</el-descriptions-item>
        </el-descriptions>

        <!-- 归还分馆选择（异地还书） -->
        <div class="branch-select-section">
          <el-form-item label="归还分馆">
            <el-select v-model="returnBranch" placeholder="选择归还分馆（异地还书）" clearable style="width: 100%">
              <el-option v-for="b in branchOptions" :key="b" :label="b" :value="b" />
            </el-select>
            <div class="form-tip">不选择则默认为本馆归还；跨分馆归还请指定归还分馆</div>
          </el-form-item>
        </div>

        <div v-if="returnInfo.fine_amount > 0" class="return-fine-info">
          <el-alert type="warning" :closable="false" show-icon>
            <template #title>
              图书逾期！预计罚款：<strong>￥{{ returnInfo.fine_amount.toFixed(2) }}</strong>
            </template>
            <template #default>
              逾期天数：{{ returnInfo.overdue_days }} 天 | 免罚天数：{{ returnInfo.grace_days || graceDaysText }}
            </template>
          </el-alert>
        </div>
        <div v-else class="return-success-info">
          <el-result icon="success" title="按时归还" sub-title="无罚款产生"></el-result>
        </div>
      </div>
      <template #footer>
        <el-button @click="showReturnDialog = false">取消</el-button>
        <el-button type="success" :loading="returnLoading" @click="confirmReturn">确认还书</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="showDetailDrawer" title="借阅记录详情" direction="rtl" size="480px">
      <div v-if="detailData" class="detail-content">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="记录ID">{{ detailData.borrow_id }}</el-descriptions-item>
          <el-descriptions-item label="读者">{{ detailData.user?.username }}
            <span class="sub-text">（证号：{{ detailData.user?.reader_card_number || '--' }}）</span>
          </el-descriptions-item>
          <el-descriptions-item label="图书">{{ detailData.book?.title }}
            <span class="sub-text">{{ detailData.book?.author }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="ISBN">{{ detailData.book?.isbn || '--' }}</el-descriptions-item>
          <el-descriptions-item label="条码号">{{ detailData.copy?.barcode }}</el-descriptions-item>
          <el-descriptions-item label="借阅时间">{{ formatDateTime(detailData.borrow_date) }}</el-descriptions-item>
          <el-descriptions-item label="应还时间">{{ formatDate(detailData.due_date) }}</el-descriptions-item>
          <el-descriptions-item label="归还时间">{{ detailData.return_date ? formatDateTime(detailData.return_date) : '未归还' }}</el-descriptions-item>
          <el-descriptions-item label="归还分馆">{{ detailData.return_branch || '本馆' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(detailData.status)">{{ detailData.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="罚款金额">￥{{ (detailData.fine_amount || 0).toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="续借次数">{{ detailData.renew_count || 0 }} 次</el-descriptions-item>
          <el-descriptions-item label="操作员">{{ detailData.operator || '系统' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, OfficeBuilding } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import request from '@/utils/request'

const userStore = useUserStore()

// ============ 权限 ============
const canBorrow = computed(() => {
  const role = userStore.userRole
  return ['super_admin', 'circulation_admin'].includes(role)
})

// ============ 数据 ============
const loading = ref(false)
const tableData = ref([])
const pagination = ref({ page: 1, size: 20, total: 0 })
const filterForm = reactive({ keyword: '', status: '' })

// 借书相关
const showBorrowDialog = ref(false)
const borrowLoading = ref(false)
const borrowRef = ref(null)
const copyBarcodeInput = ref('')
const borrowForm = reactive({ user_id: null })
const borrowRules = {
  user_id: [{ required: true, message: '请输入读者ID', trigger: 'blur' }]
}

// 读者信息
const readerInfo = ref(null)
const readerLoading = ref(false)
const eligibilityChecked = ref(false)
const eligibilityResult = ref(null)

// 已选副本
const selectedCopies = ref([])

// 添加模式：barcode（扫码） / search（搜索）
const addMode = ref('barcode')

// 图书搜索相关
const bookSearchKeyword = ref('')
const bookSearchResults = ref([])

// 副本选择器
const showCopySelectorDialog = ref(false)
const copySelectorBook = ref(null)
const availableCopies = ref([])
const copyListLoading = ref(false)
const addingBookId = ref(null)

// 续借相关
const showRenewDialog = ref(false)
const renewLoading = ref(false)
const currentBorrowId = ref(null)
const renewInfo = ref(null)

// 还书相关
const showReturnDialog = ref(false)
const returnLoading = ref(false)
const returnInfo = ref(null)
const returnBranch = ref('')
const branchOptions = ['总馆', '城东分馆', '城西分馆', '南区分馆', '北区分馆', '大学城分馆']

// 详情
const showDetailDrawer = ref(false)
const detailData = ref(null)

const graceDaysText = ref('3天')

// 是否可以提交借书
const canSubmitBorrow = computed(() => {
  return readerInfo.value && eligibilityResult.value?.eligible && selectedCopies.value.length > 0
})

// ============ 方法 ============

onMounted(() => {
  fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      size: pagination.value.size,
      keyword: filterForm.keyword || undefined,
      status_filter: filterForm.status || undefined
    }
    const res = await request.get('/borrows', { params })
    tableData.value = res.data.items
    pagination.value.total = res.data.total
  } catch (e) {
    console.error('获取借阅列表失败:', e)
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filterForm.keyword = ''
  filterForm.status = ''
  fetchData()
}

// ---- 借书 - 读者查询 ----

async function lookupReader() {
  if (!borrowForm.user_id) {
    ElMessage.warning('请输入读者ID')
    return
  }
  readerLoading.value = true
  eligibilityChecked.value = false
  eligibilityResult.value = null
  selectedCopies.value = []
  try {
    const res = await request.get(`/borrows/check-eligibility/${borrowForm.user_id}`)
    readerInfo.value = res.data.reader
    eligibilityResult.value = {
      eligible: res.data.eligible,
      reason: res.data.reason
    }
    eligibilityChecked.value = true
  } catch (e) {
    const msg = e.response?.data?.detail || '查询读者失败'
    ElMessage.error(msg)
    readerInfo.value = null
    eligibilityResult.value = null
    eligibilityChecked.value = true
  } finally {
    readerLoading.value = false
  }
}

function clearReader() {
  readerInfo.value = null
  eligibilityResult.value = null
  eligibilityChecked.value = false
  borrowForm.user_id = null
  selectedCopies.value = []
}

// ---- 借书 - 扫码添加副本 ----

async function addCopyByBarcode() {
  const barcode = copyBarcodeInput.value.trim()
  if (!barcode) return

  // 检查是否已添加
  if (selectedCopies.value.some(c => c.barcode === barcode)) {
    ElMessage.warning('该图书已在借书列表中')
    copyBarcodeInput.value = ''
    return
  }

  // 检查是否超过剩余配额
  if (readerInfo.value) {
    const remainQuota = (readerInfo.value.max_borrow_count || 0) - (selectedCopies.value.length)
    // 注意：remainQuota 还需考虑读者已有借阅
    if (selectedCopies.value.length >= readerInfo.value.max_borrow_count) {
      ElMessage.warning(`已达到最大借阅数量 ${readerInfo.value.max_borrow_count} 本`)
      return
    }
  }

  try {
    const res = await request.get('/borrows/lookup-copy', { params: { barcode } })
    const copyData = res.data

    if (copyData.status !== 'available') {
      ElMessage.warning(`该副本当前状态为"${copyData.status}"，不可借阅`)
      copyBarcodeInput.value = ''
      return
    }

    selectedCopies.value.push(copyData)
    copyBarcodeInput.value = ''
  } catch (e) {
    const msg = e.response?.data?.detail || '未找到该条码对应的图书'
    ElMessage.error(msg)
  }
}

function removeCopy(index) {
  selectedCopies.value.splice(index, 1)
}

function clearAllCopies() {
  selectedCopies.value = []
}

// ---- 借书 - 搜索图书（自动选副本） ----

async function searchBooks() {
  const keyword = bookSearchKeyword.value.trim()
  if (!keyword) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  try {
    const res = await request.get('/books/search', { params: { query: keyword, size: 20 } })
    bookSearchResults.value = res.data.items || []
    if (bookSearchResults.value.length === 0) {
      ElMessage.info('未找到匹配的图书')
    }
  } catch {
    ElMessage.error('搜索图书失败')
  }
}

async function addBookDirectly(book) {
  addingBookId.value = book.book_id
  try {
    // 获取该书的副本列表
    const res = await request.get(`/books/${book.book_id}`)
    const allCopies = res.data.copies || []
    const selectedCopyIds = selectedCopies.value.map(c => c.copy_id)
    const available = allCopies.filter(
      c => c.status === 'available' && !selectedCopyIds.includes(c.copy_id)
    )
    if (available.length === 0) {
      ElMessage.warning('没有可借的副本')
      return
    }
    // 只有一本可用，直接添加
    if (available.length === 1) {
      doAddCopy(available[0], book)
      return
    }
    // 多本可用，弹出选择
    copySelectorBook.value = book
    availableCopies.value = available
    showCopySelectorDialog.value = true
  } catch {
    ElMessage.error('获取副本信息失败')
  } finally {
    addingBookId.value = null
  }
}

function doAddCopy(copy, book) {
  if (selectedCopies.value.some(c => c.copy_id === copy.copy_id)) {
    ElMessage.warning('该副本已在借书列表中')
    return
  }
  selectedCopies.value.push({
    copy_id: copy.copy_id,
    barcode: copy.barcode,
    status: copy.status,
    title: book.title,
    author: book.author,
    book_id: book.book_id,
    isbn: book.isbn,
  })
  ElMessage.success(`已添加《${book.title}》`)
}

function addCopyFromSelector(copy) {
  if (!copySelectorBook.value) return
  doAddCopy(copy, copySelectorBook.value)
  showCopySelectorDialog.value = false
}

// ---- 借书 - 提交 ----

async function submitBorrow() {
  if (!borrowRef.value) return
  await borrowRef.value.validate()

  if (selectedCopies.value.length === 0) {
    ElMessage.warning('请至少添加一本图书')
    return
  }

  borrowLoading.value = true
  try {
    const copyIds = selectedCopies.value.map(c => c.copy_id)

    if (copyIds.length === 1) {
      await request.post('/borrows', {
        user_id: borrowForm.user_id,
        copy_id: copyIds[0]
      })
      ElMessage.success('借书成功')
    } else {
      const res = await request.post('/borrows/batch', {
        user_id: borrowForm.user_id,
        copy_ids: copyIds
      })
      if (res.fail_count > 0) {
        ElMessage.warning(`成功${res.success_count}本，失败${res.fail_count}本`)
      } else {
        ElMessage.success(`批量借书成功，共${res.success_count || copyIds.length}本`)
      }
    }
    showBorrowDialog.value = false
    resetBorrowForm()
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '借书失败')
  } finally {
    borrowLoading.value = false
  }
}

function resetBorrowForm() {
  borrowForm.user_id = null
  copyBarcodeInput.value = ''
  readerInfo.value = null
  eligibilityResult.value = null
  eligibilityChecked.value = false
  selectedCopies.value = []
  bookSearchKeyword.value = ''
  bookSearchResults.value = []
  addMode.value = 'barcode'
  borrowRef.value?.resetFields()
}

// ---- 续借 ----

async function handleRenew(row) {
  currentBorrowId.value = row.borrow_id
  try {
    const res = await request.get(`/borrows/${row.borrow_id}/overdue-info`)
    renewInfo.value = {
      ...row,
      due_date: res.data.due_date,
      max_renew_count: 2,
      renew_days: 15
    }
  } catch {
    renewInfo.value = { ...row, max_renew_count: 2, renew_days: 15 }
  }
  showRenewDialog.value = true
}

async function confirmRenew() {
  renewLoading.value = true
  try {
    const res = await request.post(`/borrows/${currentBorrowId.value}/renew`)
    ElMessage.success(res.message || '续借成功')
    showRenewDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '续借失败')
  } finally {
    renewLoading.value = false
  }
}

// ---- 还书 ----

async function handleReturn(row) {
  currentBorrowId.value = row.borrow_id
  returnBranch.value = ''
  try {
    const res = await request.get(`/borrows/${row.borrow_id}/overdue-info`)
    returnInfo.value = {
      ...res.data,
      title: row.title,
      return_date: new Date().toLocaleDateString()
    }
  } catch {
    returnInfo.value = { title: row.title, fine_amount: 0, overdue_days: 0, due_date: row.due_date }
  }
  showReturnDialog.value = true
}

async function confirmReturn() {
  returnLoading.value = true
  try {
    const res = await request.post(`/borrows/${currentBorrowId.value}/return`, {
      return_branch: returnBranch.value || undefined
    })
    const data = res.data
    let alertMsg = '还书成功！'
    if (data.fine_amount > 0) {
      alertMsg += `<br/>逾期 ${data.overdue_days} 天<br/>罚款 ￥${data.fine_amount.toFixed(2)}<br/>请在罚款管理中缴纳`
    }
    if (data.auto_frozen) {
      alertMsg += `<br/><span style="color:#F56C6C;font-weight:bold">累计罚款已达冻结阈值，借阅权限已被自动冻结</span>`
    }
    if (data.return_branch) {
      alertMsg += `<br/>归还分馆：${data.return_branch}`
    }
    if (data.has_reservation) {
      alertMsg += `<br/>已触发预约流转，通知预约读者取书`
    }

    if (data.fine_amount > 0 || data.auto_frozen) {
      ElMessageBox.alert(alertMsg, '还书结果', { dangerouslyUseHTMLString: true, type: data.auto_frozen ? 'error' : 'warning' })
    } else {
      ElMessage.success(res.message || '还书成功，无罚款')
    }
    showReturnDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '还书失败')
  } finally {
    returnLoading.value = false
  }
}

// ---- 详情 ----

async function showDetail(row) {
  try {
    const res = await request.get(`/borrows/${row.borrow_id}`)
    detailData.value = res.data
    showDetailDrawer.value = true
  } catch {
    ElMessage.error('获取详情失败')
  }
}

// ---- 工具 ----

function getStatusTagType(status) {
  const map = { active: '', returned: 'info', overdue: 'danger', lost: 'warning' }
  return map[status] || 'info'
}

function formatDate(d) {
  if (!d) return '--'
  return new Date(d).toLocaleDateString()
}

function formatDateTime(d) {
  if (!d) return '--'
  return new Date(d).toLocaleString()
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

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.text-danger { color: #F56C6C; }
.text-muted { color: #909399; font-size: 12px; }

.reader-info-card {
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-top: 8px;

  .eligibility-result {
    margin-top: 12px;
  }
}

.copy-input-area {
  width: 100%;
}

.selected-copies-section {
  margin-top: 12px;

  .section-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 8px;
    color: #303133;
  }
}

.add-mode-switch {
  margin-bottom: 12px;
}

.book-search-results {
  margin-top: 4px;

  .section-title {
    font-size: 13px;
    color: #606266;
    margin-bottom: 8px;
  }
}

.copy-input-section {
  padding: 0 0 0 100px;
}

.return-fine-info { margin-top: 16px; }
.return-success-info { margin-top: 16px; }

.branch-select-section {
  margin-top: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;

  .form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
  }
}

.branch-tag {
  color: #409EFF;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.detail-content {
  .sub-text {
    color: #909399;
    font-size: 13px;
    margin-left: 6px;
  }
}
</style>
