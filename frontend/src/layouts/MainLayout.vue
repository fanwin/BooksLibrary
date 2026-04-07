<template>
  <div class="main-layout">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside :width="isCollapse ? '64px' : '240px'" class="sidebar">
        <div class="logo">
          <el-icon size="32" color="#409EFF"><Reading /></el-icon>
          <span v-show="!isCollapse" class="logo-text">图书馆管理系统</span>
        </div>
        
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapse"
          :collapse-transition="false"
          router
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/dashboard">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>{{ isSuperAdmin || isAdmin ? '运营看板' : '我的看板' }}</template>
          </el-menu-item>
          
          <el-menu-item index="/books">
            <el-icon><Notebook /></el-icon>
            <template #title>图书管理</template>
          </el-menu-item>
          
          <el-menu-item index="/borrows">
            <el-icon><Document /></el-icon>
            <template #title>借阅管理</template>
          </el-menu-item>
          
          <el-menu-item index="/reservations">
            <el-icon><Clock /></el-icon>
            <template #title>预约管理</template>
          </el-menu-item>
          
          <el-menu-item index="/fines">
            <el-icon><Money /></el-icon>
            <template #title>罚款管理</template>
          </el-menu-item>
          
          <el-menu-item index="/statistics" v-if="canViewStatistics">
            <el-icon><TrendCharts /></el-icon>
            <template #title>统计分析</template>
          </el-menu-item>
          
          <el-menu-item index="/categories">
            <el-icon><Menu /></el-icon>
            <template #title>分类管理</template>
          </el-menu-item>
          
          <el-menu-item index="/purchase-requests">
            <el-icon><ShoppingCart /></el-icon>
            <template #title>荐购管理</template>
          </el-menu-item>
          
          <el-menu-item index="/recommendations">
            <el-icon><StarFilled /></el-icon>
            <template #title>图书推荐</template>
          </el-menu-item>
          
          <el-menu-item index="/logs" v-if="isAdmin || userStore.userRole === 'auditor'">
            <el-icon><Document /></el-icon>
            <template #title>系统日志</template>
          </el-menu-item>

          <el-sub-menu index="/system" v-if="isSuperAdmin || isAdmin">
            <template #title>
              <el-icon><Tools /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item index="/system/holidays" v-if="isAdmin">
              <el-icon><Calendar /></el-icon>
              <template #title>节假日管理</template>
            </el-menu-item>
            <el-menu-item index="/system/configs" v-if="isSuperAdmin">
              <el-icon><Setting /></el-icon>
              <template #title>系统配置</template>
            </el-menu-item>
            <el-menu-item index="/system/users" v-if="isSuperAdmin">
              <el-icon><User /></el-icon>
              <template #title>用户管理</template>
            </el-menu-item>
            <el-menu-item index="/system/roles" v-if="isSuperAdmin">
              <el-icon><Lock /></el-icon>
              <template #title>权限管理</template>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-aside>
      
      <!-- 主内容区 -->
      <el-container>
        <!-- 顶部导航 -->
        <el-header class="header">
          <div class="header-left">
            <el-icon class="collapse-btn" @click="toggleCollapse">
              <Fold v-if="!isCollapse" />
              <Expand v-else />
            </el-icon>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item v-if="route.meta.parentTitle">{{ route.meta.parentTitle }}</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          
          <div class="header-right">
            <NotificationBell />
            <el-dropdown @command="handleCommand">
              <span class="user-info">
                <el-avatar :size="32" :icon="UserFilled" />
                <span class="username">{{ userStore.username }}</span>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                  <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>
        
        <!-- 内容区域 -->
        <el-main class="main-content">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { 
  Reading, DataAnalysis, Notebook, Document, Clock, 
  Money, TrendCharts, Menu, ShoppingCart, User,
  Fold, Expand, UserFilled, StarFilled, Calendar, Setting, Lock, Tools, Search
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import NotificationBell from '@/components/NotificationBell.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '')
const isAdmin = computed(() => {
  const role = userStore.userRole
  return ['super_admin', 'catalog_admin', 'circulation_admin'].includes(role)
})
const isSuperAdmin = computed(() => userStore.userRole === 'super_admin')
const canViewStatistics = computed(() => {
  const role = userStore.userRole
  return ['super_admin', 'catalog_admin', 'circulation_admin', 'auditor'].includes(role)
})

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const handleCommand = async (command) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      userStore.logout()
      router.push('/login')
    } catch {
      // 取消退出
    }
  } else if (command === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped lang="scss">
.main-layout {
  width: 100%;
  height: 100vh;
}

.el-container {
  height: 100%;
}

.sidebar {
  background-color: #304156;
  transition: width 0.3s;
  overflow-x: hidden;
  
  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    background-color: #2b3a4a;
    
    .logo-text {
      font-size: 18px;
      font-weight: bold;
      color: #fff;
      white-space: nowrap;
    }
  }
  
  .el-menu {
    border-right: none;
  }
}

.header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 20px;
    
    .collapse-btn {
      font-size: 20px;
      cursor: pointer;
      transition: color 0.3s;
      
      &:hover {
        color: #409EFF;
      }
    }
  }
  
  .header-right {
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      
      .username {
        font-size: 14px;
        color: #606266;
      }
    }
  }
}

.main-content {
  background-color: #f5f7fa;
  overflow-y: auto;
}

// 过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
