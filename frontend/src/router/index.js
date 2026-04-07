import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '运营看板' }
      },
      {
        path: 'books',
        name: 'Books',
        component: () => import('@/views/books/BookList.vue'),
        meta: { title: '图书管理' }
      },
      {
        path: 'borrows',
        name: 'Borrows',
        component: () => import('@/views/borrows/BorrowList.vue'),
        meta: { title: '借阅管理' }
      },
      {
        path: 'reservations',
        name: 'Reservations',
        component: () => import('@/views/reservations/ReservationList.vue'),
        meta: { title: '预约管理' }
      },
      {
        path: 'fines',
        name: 'Fines',
        component: () => import('@/views/fines/FineList.vue'),
        meta: { title: '罚款管理' }
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('@/views/statistics/Statistics.vue'),
        meta: { title: '统计分析', roles: ['super_admin', 'catalog_admin', 'circulation_admin', 'auditor'] }
      },
      {
        path: 'system',
        name: 'System',
        redirect: '/system/configs',
        meta: { title: '系统管理' },
        children: [
          {
            path: 'holidays',
            name: 'Holidays',
            component: () => import('@/views/system/HolidayManage.vue'),
            meta: { title: '节假日管理', parentTitle: '系统管理', roles: ['super_admin', 'catalog_admin', 'circulation_admin'] }
          },
          {
            path: 'configs',
            name: 'SystemConfigs',
            component: () => import('@/views/system/SystemConfigManage.vue'),
            meta: { title: '系统配置', parentTitle: '系统管理', roles: ['super_admin'] }
          },
          {
            path: 'users',
            name: 'Users',
            component: () => import('@/views/users/UserList.vue'),
            meta: { title: '用户管理', parentTitle: '系统管理', roles: ['super_admin'] }
          },
          {
            path: 'roles',
            name: 'Roles',
            component: () => import('@/views/system/RoleManage.vue'),
            meta: { title: '权限管理', parentTitle: '系统管理', roles: ['super_admin'] }
          },
        ]
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/system/SystemLogs.vue'),
        meta: { title: '系统日志', roles: ['super_admin', 'auditor'] }
      },
      {
        path: 'categories',
        name: 'Categories',
        component: () => import('@/views/system/CategoryManage.vue'),
        meta: { title: '分类管理' }
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/system/Notifications.vue'),
        meta: { title: '消息通知' }
      },
      {
        path: 'purchase-requests',
        name: 'PurchaseRequests',
        component: () => import('@/views/purchase/PurchaseRequests.vue'),
        meta: { title: '荐购管理' }
      },
      {
        path: 'recommendations',
        name: 'Recommendations',
        component: () => import('@/views/books/RecommendationPanel.vue'),
        meta: { title: '图书推荐' }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue'),
        meta: { title: '个人中心' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth !== false) {
    if (!userStore.isLoggedIn) {
      next('/login')
    } else {
      if (!userStore.userInfo) {
        try {
          await userStore.getUserInfo()
        } catch (error) {
          next('/login')
          return
        }
      }
      
      // 基于角色的权限检查
      if (to.meta.roles && !to.meta.roles.includes(userStore.userRole)) {
        // 读者无权访问时跳转到个人中心
        next('/profile')
      } else {
        next()
      }
    }
  } else {
    if (userStore.isLoggedIn && (to.path === '/login' || to.path === '/register')) {
      next('/dashboard')
    } else {
      next()
    }
  }
})

export default router
