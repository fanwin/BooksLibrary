<template>
  <div class="notification-bell">
    <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
      <el-icon class="bell-icon" @click.stop="showPanel = !showPanel" :size="20">
        <Bell />
      </el-icon>
    </el-badge>

    <!-- 通知面板 -->
    <transition name="slide">
      <div v-if="showPanel" class="notification-panel" @click.stop>
        <div class="panel-header">
          <span class="panel-title">消息通知</span>
          <div class="panel-actions">
            <el-button type="primary" link size="small" @click="handleMarkAllRead" :disabled="unreadCount === 0">
              全部已读
            </el-button>
            <el-button type="info" link size="small" @click="goToFullList">
              查看全部
            </el-button>
          </div>
        </div>

        <div class="panel-list" v-loading="loading">
          <template v-if="recentNotifications.length > 0">
            <div
              v-for="n in recentNotifications"
              :key="n.notification_id"
              class="notification-item"
              :class="{ unread: !n.is_read }"
              @click="handleRead(n)"
            >
              <div class="item-dot" v-if="!n.is_read"></div>
              <div class="item-content">
                <div class="item-title">{{ n.title }}</div>
                <div class="item-desc" v-if="n.content">{{ n.content }}</div>
                <div class="item-time">{{ formatTime(n.created_at) }}</div>
              </div>
            </div>
          </template>
          <div v-else class="empty-state">
            <el-empty description="暂无新消息" :image-size="60" />
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import request from '@/utils/request'

const router = useRouter()
const showPanel = ref(false)
const loading = ref(false)
const unreadCount = ref(0)
const recentNotifications = ref([])

let pollTimer = null

onMounted(() => {
  fetchUnreadCount()
  fetchRecent()
  // 每30秒刷新一次
  pollTimer = setInterval(() => {
    fetchUnreadCount()
  }, 30000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// 点击外部关闭面板
function handleClickOutside(e) {
  showPanel.value = false
}
document.addEventListener('click', handleClickOutside)

async function fetchUnreadCount() {
  try {
    const res = await request.get('/notifications/unread-count')
    unreadCount.value = res.data?.count || 0
  } catch {
    // 静默
  }
}

async function fetchRecent() {
  loading.value = true
  try {
    const res = await request.get('/notifications', { params: { page: 1, size: 10 } })
    recentNotifications.value = res.data?.items || []
    unreadCount.value = res.data?.unread_count || 0
  } catch {
    // 静默
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
    recentNotifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
  } catch {
    // 静默
  }
}

function goToFullList() {
  showPanel.value = false
  router.push('/notifications')
}

function formatTime(timeStr) {
  if (!timeStr) return ''
  try {
    const now = new Date()
    const time = new Date(timeStr)
    const diff = now - time
    const minutes = Math.floor(diff / 60000)
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}小时前`
    const days = Math.floor(hours / 24)
    if (days < 7) return `${days}天前`
    return time.toLocaleDateString('zh-CN')
  } catch {
    return timeStr
  }
}
</script>

<style scoped lang="scss">
.notification-bell {
  position: relative;
  margin-right: 16px;
}

.bell-icon {
  cursor: pointer;
  color: #606266;
  transition: color 0.2s;
  &:hover {
    color: #409EFF;
  }
}

.notification-panel {
  position: absolute;
  top: 40px;
  right: 0;
  width: 380px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  z-index: 3000;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;

  .panel-title {
    font-weight: 600;
    font-size: 15px;
    color: #303133;
  }

  .panel-actions {
    display: flex;
    gap: 4px;
  }
}

.panel-list {
  max-height: 400px;
  overflow-y: auto;
  min-height: 200px;
}

.notification-item {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid #f5f5f5;

  &:hover {
    background: #f5f7fa;
  }

  &.unread {
    background: #ecf5ff;
    &:hover {
      background: #d9ecff;
    }
  }
}

.item-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #409EFF;
  margin-top: 6px;
  flex-shrink: 0;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-desc {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-time {
  font-size: 11px;
  color: #c0c4cc;
}

.empty-state {
  padding: 40px 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
