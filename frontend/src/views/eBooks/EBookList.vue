<template>
  <div class="ebook-list page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>电子书管理</span>
          <el-button type="primary" @click="handleAdd" v-if="canManage">
            <el-icon><Plus /></el-icon>添加电子书
          </el-button>
        </div>
      </template>
      
      <!-- 搜索栏 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="书名">
          <el-input v-model="searchForm.title" placeholder="请输入书名" clearable />
        </el-form-item>
        <el-form-item label="作者">
          <el-input v-model="searchForm.author" placeholder="请输入作者" clearable />
        </el-form-item>
        <el-form-item label="ISBN">
          <el-input v-model="searchForm.isbn" placeholder="请输入ISBN" clearable />
        </el-form-item>
        <el-form-item label="格式">
          <el-select v-model="searchForm.file_format" placeholder="请选择格式" clearable>
            <el-option label="PDF" value="pdf" />
            <el-option label="EPUB" value="epub" />
            <el-option label="MOBI" value="mobi" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadEbooks">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      
      <!-- 表格 -->
      <el-table :data="ebooks" style="width: 100%" v-loading="loading">
        <el-table-column prop="ebook_id" label="ID" width="80" />
        <el-table-column prop="title" label="书名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="author" label="作者" width="150" />
        <el-table-column prop="isbn" label="ISBN" width="150" />
        <el-table-column prop="file_format" label="格式" width="100" />
        <el-table-column prop="file_size" label="大小" width="100" align="center">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_copies" label="总馆藏" width="100" align="center" />
        <el-table-column prop="available_copies" label="可借" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.available_copies > 0 ? 'success' : 'danger'">
              {{ row.available_copies }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="350" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleView(row)">查看</el-button>
            <el-button
              v-if="row.available_copies > 0 && isLoggedIn"
              size="small"
              type="primary"
              @click="handleBorrow(row)"
            >借阅</el-button>
            <el-button
              v-if="row.available_copies <= 0 && isLoggedIn"
              size="small"
              type="warning"
              @click="handleReserve(row)"
            >预约</el-button>
            <el-button size="small" type="primary" @click="handleEdit(row)" v-if="canManage">编辑</el-button>
            <el-popconfirm
              v-if="canManage"
              title="确认永久删除该电子书？此操作不可恢复！"
              confirm-button-text="确认删除"
              cancel-button-text="取消"
              confirm-button-type="danger"
              @confirm="handlePhysicalDelete(row)"
            >
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadEbooks"
        @current-change="loadEbooks"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="700px"
      @close="handleDialogClose"
    >
      <el-form :model="ebookForm" :rules="rules" ref="formRef" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="书名" prop="title">
              <el-input v-model="ebookForm.title" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="ISBN" prop="isbn">
              <el-input v-model="ebookForm.isbn" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="作者" prop="author">
              <el-input v-model="ebookForm.author" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="出版社">
              <el-input v-model="ebookForm.publisher" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="出版年份">
              <el-input-number v-model="ebookForm.publish_year" :min="1900" :max="2030" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="文件格式" prop="file_format">
              <el-select v-model="ebookForm.file_format" placeholder="请选择文件格式">
                <el-option label="PDF" value="pdf" />
                <el-option label="EPUB" value="epub" />
                <el-option label="MOBI" value="mobi" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="文件大小（字节）">
              <el-input-number v-model="ebookForm.file_size" :min="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="副本数量">
              <el-input-number v-model="ebookForm.total_copies" :min="1" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="文件路径" prop="file_path">
          <el-input v-model="ebookForm.file_path" />
        </el-form-item>
        
        <el-form-item label="索书号">
          <el-input v-model="ebookForm.call_number" />
        </el-form-item>
        
        <el-form-item label="简介">
          <el-input v-model="ebookForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 查看详情对话框 -->
    <el-dialog v-model="viewVisible" title="电子书详情" width="650px">
      <el-descriptions :column="2" border v-if="viewData" v-loading="viewLoading">
        <el-descriptions-item label="书名" :span="2">{{ viewData.title }}</el-descriptions-item>
        <el-descriptions-item label="作者">{{ viewData.author || '-' }}</el-descriptions-item>
        <el-descriptions-item label="ISBN">{{ viewData.isbn || '-' }}</el-descriptions-item>
        <el-descriptions-item label="出版社">{{ viewData.publisher || '-' }}</el-descriptions-item>
        <el-descriptions-item label="出版年份">{{ viewData.publish_year || '-' }}</el-descriptions-item>
        <el-descriptions-item label="分类">{{ viewData.category_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="文件格式">{{ viewData.file_format }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ formatFileSize(viewData.file_size) }}</el-descriptions-item>
        <el-descriptions-item label="索书号">{{ viewData.call_number || '-' }}</el-descriptions-item>
        <el-descriptions-item label="总馆藏">{{ viewData.total_copies }}</el-descriptions-item>
        <el-descriptions-item label="可借数量">
          <el-tag :type="viewData.available_copies > 0 ? 'success' : 'danger'" size="small">
            {{ viewData.available_copies }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(viewData.status)" size="small">{{ getStatusText(viewData.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="文件路径" :span="2">{{ viewData.file_path }}</el-descriptions-item>
        <el-descriptions-item label="简介" :span="2">{{ viewData.description || '暂无简介' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, ElIcon } from 'element-plus'
import request from '@/utils/request'

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加电子书')
const formRef = ref(null)
const viewVisible = ref(false)
const viewLoading = ref(false)
const viewData = ref(null)

const canManage = computed(() => {
  const role = userStore.userRole
  return ['super_admin', 'catalog_admin'].includes(role)
})

const isLoggedIn = computed(() => userStore.isLoggedIn)

const ebooks = ref([])
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const searchForm = reactive({
  title: '',
  author: '',
  isbn: '',
  file_format: ''
})

const ebookForm = reactive({
  ebook_id: null,
  title: '',
  author: '',
  isbn: '',
  publisher: '',
  publish_year: new Date().getFullYear(),
  file_format: 'pdf',
  file_size: 0,
  file_path: '',
  call_number: '',
  description: '',
  total_copies: 1
})

const rules = {
  title: [{ required: true, message: '请输入书名', trigger: 'blur' }],
  file_format: [{ required: true, message: '请选择文件格式', trigger: 'blur' }],
  file_path: [{ required: true, message: '请输入文件路径', trigger: 'blur' }]
}

const getStatusType = (status) => {
  const types = {
    available: 'success',
    borrowed: 'warning',
    reserved: 'info',
    withdrawn: 'danger'
  }
  return types[status] || ''
}

const getStatusText = (status) => {
  const texts = {
    available: '在馆',
    borrowed: '借出',
    reserved: '预约',
    damaged: '损坏',
    lost: '遗失',
    withdrawn: '下架'
  }
  return texts[status] || status
}

const formatFileSize = (size) => {
  if (!size) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let unitIndex = 0
  let currentSize = size
  while (currentSize >= 1024 && unitIndex < units.length - 1) {
    currentSize /= 1024
    unitIndex++
  }
  return `${currentSize.toFixed(2)} ${units[unitIndex]}`
}

const loadEbooks = async () => {
  loading.value = true
  try {
    const res = await request.get('/ebooks', {
      params: {
        page: pagination.page,
        size: pagination.size,
        ...searchForm
      }
    })
    ebooks.value = res.data.items
    pagination.total = res.data.total
  } catch (error) {
    console.error('加载电子书列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  searchForm.title = ''
  searchForm.author = ''
  searchForm.isbn = ''
  searchForm.file_format = ''
  pagination.page = 1
  loadEbooks()
}

const handleAdd = () => {
  dialogTitle.value = '添加电子书'
  dialogVisible.value = true
  Object.keys(ebookForm).forEach(key => {
    ebookForm[key] = key === 'publish_year' ? new Date().getFullYear() : 
                    key === 'total_copies' ? 1 : 
                    key === 'file_size' ? 0 : 
                    key === 'file_format' ? 'pdf' : ''
  })
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑电子书'
  dialogVisible.value = true
  Object.assign(ebookForm, row)
}

const handleView = async (row) => {
  viewVisible.value = true
  viewLoading.value = true
  viewData.value = null
  try {
    const res = await request.get(`/ebooks/${row.ebook_id}`)
    viewData.value = res.data
  } catch (error) {
    console.error('加载电子书详情失败:', error)
    ElMessage.error('加载详情失败')
  } finally {
    viewLoading.value = false
  }
}

const handleBorrow = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要借阅《${row.title}》吗？`,
      '借阅确认',
      { confirmButtonText: '确定借阅', cancelButtonText: '取消', type: 'info' }
    )
    await request.post(`/ebooks/${row.ebook_id}/borrow`)
    ElMessage.success('借阅成功！')
    loadEbooks()
  } catch (e) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || '借阅失败')
    }
  }
}

const handleReserve = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要预约《${row.title}》吗？预约后，当有副本可用时系统会通知您。`,
      '预约确认',
      { confirmButtonText: '确定预约', cancelButtonText: '取消', type: 'info' }
    )
    await request.post('/reservations', {
      user_id: userStore.userInfo?.user_id || userStore.userId,
      book_id: row.ebook_id
    })
    ElMessage.success('预约成功！请留意消息通知。')
  } catch (e) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || '预约失败')
    }
  }
}

const handlePhysicalDelete = async (row) => {
  try {
    await request.delete(`/ebooks/${row.ebook_id}`)
    ElMessage.success(`电子书「${row.title}」已删除`)
    loadEbooks()
  } catch (error) {
    const msg = error.response?.data?.detail || error.message || '删除失败'
    ElMessage.error(msg)
  }
}

const handleSubmit = async () => {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return
    
    submitting.value = true
    
    if (ebookForm.ebook_id) {
      await request.put(`/ebooks/${ebookForm.ebook_id}`, ebookForm)
      ElMessage.success('更新成功')
    } else {
      await request.post('/ebooks', ebookForm)
      ElMessage.success('添加成功')
    }
    
    dialogVisible.value = false
    loadEbooks()
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitting.value = false
  }
}

const handleDialogClose = () => {
  formRef.value?.resetFields()
}

onMounted(() => {
  loadEbooks()
})
</script setup>