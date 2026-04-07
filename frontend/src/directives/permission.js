/**
 * 权限指令 v-permission
 * 用法：
 *   v-permission="'book:create'"           - 单权限
 *   v-permission="['book:create', 'book:update']"  - 多权限（任一满足即可）
 *   v-permission.all="['book:create', 'book:update']"  - 多权限（必须全部满足）
 */
import { useUserStore } from '@/stores/user'

const checkPermission = (permissions, mode) => {
  const userStore = useUserStore()
  if (userStore.userRole === 'super_admin') return true

  const perms = Array.isArray(permissions) ? permissions : [permissions]
  if (mode === 'all') {
    return perms.every(p => userStore.permissions.includes(p))
  }
  return perms.some(p => userStore.permissions.includes(p))
}

const permissionDirective = {
  mounted(el, binding) {
    const { value, modifiers } = binding
    const mode = modifiers.all ? 'all' : 'any'
    if (!checkPermission(value, mode)) {
      el.parentNode && el.parentNode.removeChild(el)
    }
  },
  updated(el, binding) {
    const { value, modifiers } = binding
    const mode = modifiers.all ? 'all' : 'any'
    if (!checkPermission(value, mode)) {
      el.parentNode && el.parentNode.removeChild(el)
    }
  }
}

export default permissionDirective
