<template>
  <div class="notification-page page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>消息通知</span>
          <div class="header-actions">
            <el-select v-model="filterRead" placeholder="全部" clearable style="width: 120px" @change="fetchData">
              <el-option label="未读" :value="false" />
              <el-option label="已读" :value="true" />
            </el-select>
            <el-button type="primary" link @click="handleMarkAllRead" :disabled="unreadCount === 0">
              全部标记已读
            </el-button>
          </div>
        </div>
      </template>

      <!-- 统计 -->
      <div class="stats-row">
        <div class="stat-card unread">
          <span class="stat-num">{{ unreadCount }}</span>
          <span class="stat-label">未读消息</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ total }}</span>
          <span class="stat-label">全部消息</span>
        </div>
      </div>

      <!-- 列表 -->
      <div class="notification-list" v-loading="loading">
        <div
          v-for="n in notifications"
          :key="n.notification_id"
          class="notification-item"
          :class="{ unread: !n.is_read }"
          @click="handleRead(n)"
        >
          <div class="item-indicator" v-if="!n.is_read"></div>
          <div class="item-body">
            <div class="item-header">
              <span class="item-title">{{ n.title }}</span>
              <el-tag v-if="n.type" :type="getTagType(n.type)" size="small" effect="plain">{{ getTypeText(n.type) }}</el-tag>
            </div>
            <div class="item-content" v-if="n.content">{{ n.content }}</div>
            <div class="item-footer">
              <span class="item-time">{{ formatTime(n.created_at) }}</span>
              <el-button size="small" type="danger" link @click.stop="handleDelete(n)">删除</el-button>
            </div>
          </div>
        </div>

        <el-empty v-if="!loading && notifications.length === 0" description="暂无通知" />
      </div>

      <!-- 分页 -->
      <div class="pagination-wrapper" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :total="total"
          :page-size="pageSize"
          layout="prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const loading = ref(false)
const notifications = ref([])
const total = ref(0)
const unreadCount = ref(0)
const currentPage = ref(1)
const pageSize = 20
const filterRead = ref(null)

onMounted(() => fetchData())

async function fetchData() {
  loading.value = true
  try {
    const params = { page: currentPage.value, size: pageSize }
    if (filterRead.value !== null && filterRead.value !== '') {
      params.is_read = filterRead.value
    }
    const res = await request.get('/notifications', { params })
    notifications.value = res.data?.items || []
    total.value = res.data?.total || 0
    unreadCount.value = res.data?.unread_count || 0
  } catch (e) {
    console.error('获取通知失败:', e)
  } finally {
    loading.value = false
  }
}

async function handleRead(notification) {
  if (!notification.is_read) {
    try {
      await request.put(`/notifications/${notification.notification_id}/read`)
      notification.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch {
      // 静默
    }
  }
}

async function handleMarkAllRead() {
  try {
    await request.put('/notifications/read-all')
    notifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
    ElMessage.success('已全部标记为已读')
  } catch {
    // 静默
  }
}

async function handleDelete(n) {
  try {
    await ElMessageBox.confirm('确定删除此通知？', '确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await request.delete(`/notifications/${n.notification_id}`)
    ElMessage.success('通知已删除')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function getTagType(type) {
  return { system: 'info', borrow: 'success', fine: 'danger', reservation: 'warning' }[type] || 'info'
}

function getTypeText(type) {
  return { system: '系统', borrow: '借阅', fine: '罚款', reservation: '预约' }[type] || type
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
  border-left: 3px solid #dcdfe6;

  .stat-num {
    display: block;
    font-size: 24px;
    font-weight: bold;
    color: #303133;
  }

  .stat-label {
    font-size: 13px;
    color: #909399;
    margin-top: 2px;
  }

  &.unread {
    border-left-color: #409EFF;
    .stat-num { color: #409EFF; }
  }
}

.notification-list {
  min-height: 300px;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  &.unread {
    background: #ecf5ff;
    border-color: #b3d8ff;
  }
}

.item-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #409EFF;
  margin-top: 6px;
  flex-shrink: 0;
}

.item-body {
  flex: 1;
  min-width: 0;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.item-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.item-content {
  font-size: 14px;
  color: #606266;
  line-height: 1.5;
  margin-bottom: 8px;
}

.item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-time {
  font-size: 12px;
  color: #c0c4cc;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
</style>
