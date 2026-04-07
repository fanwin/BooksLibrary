<template>
  <div class="role-manage">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">权限管理</span>
          <div class="actions">
            <el-button type="primary" :icon="Refresh" @click="initDefaultRoles" :loading="initLoading">
              初始化默认角色
            </el-button>
            <el-button type="success" :icon="Plus" @click="showCreateDialog">
              创建角色
            </el-button>
          </div>
        </div>
      </template>

      <!-- 角色列表 -->
      <el-table :data="roles" v-loading="loading" border stripe>
        <el-table-column prop="role_id" label="ID" width="80" />
        <el-table-column prop="role_name" label="角色名称" width="180" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="权限数量" width="100" align="center">
          <template #default="{ row }">
            <el-tag>{{ row.permissions ? row.permissions.length : 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ row.created_at ? row.created_at.slice(0, 19).replace('T', ' ') : '' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showEditDialog(row)">
              编辑权限
            </el-button>
            <el-button
              type="danger"
              link
              size="small"
              @click="handleDelete(row)"
              :disabled="isBuiltinRole(row.role_name)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 权限详情面板 -->
    <el-card shadow="never" style="margin-top: 16px" v-if="selectedRole">
      <template #header>
        <div class="card-header">
          <span class="title">{{ selectedRole.role_name }} - 权限配置</span>
          <el-tag :type="isBuiltinRole(selectedRole.role_name) ? 'warning' : 'info'" size="small">
            {{ isBuiltinRole(selectedRole.role_name) ? '系统内置' : '自定义' }}
          </el-tag>
        </div>
      </template>

      <el-form :model="editForm" label-width="120px">
        <el-form-item label="角色名称">
          <el-input v-model="editForm.role_name" :disabled="isBuiltinRole(selectedRole.role_name)" />
        </el-form-item>
        <el-form-item label="角色描述">
          <el-input v-model="editForm.description" placeholder="请输入角色描述" />
        </el-form-item>
        <el-form-item label="权限配置">
          <div class="permission-groups">
            <div v-for="group in permissionGroups" :key="group.name" class="permission-group">
              <div class="group-header">
                <el-checkbox
                  :model-value="isGroupAllChecked(group)"
                  :indeterminate="isGroupIndeterminate(group)"
                  @change="(val) => toggleGroup(group, val)"
                >
                  <strong>{{ group.label }}</strong>
                </el-checkbox>
              </div>
              <div class="group-items">
                <el-checkbox-group v-model="editForm.permissions">
                  <el-checkbox
                    v-for="perm in group.permissions"
                    :key="perm"
                    :label="perm"
                    class="perm-checkbox"
                  >
                    {{ formatPermissionLabel(perm) }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="savePermissions" :loading="saveLoading">
            保存修改
          </el-button>
          <el-button @click="selectedRole = null">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 创建角色对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建新角色" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="角色名称">
          <el-input v-model="createForm.role_name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="角色描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="请输入角色描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createRole" :loading="createLoading">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const roles = ref([])
const allPermissions = ref([])
const defaultPermissions = ref({})
const selectedRole = ref(null)
const saveLoading = ref(false)
const initLoading = ref(false)
const createDialogVisible = ref(false)
const createLoading = ref(false)

const editForm = reactive({
  role_name: '',
  description: '',
  permissions: []
})

const createForm = reactive({
  role_name: '',
  description: ''
})

const BUILTIN_ROLES = ['super_admin', 'catalog_admin', 'circulation_admin', 'reader', 'auditor']
const isBuiltinRole = (name) => BUILTIN_ROLES.includes(name)

const PERMISSION_GROUP_MAP = {
  'dashboard': '运营看板',
  'book': '图书管理',
  'borrow': '借阅管理',
  'user': '用户管理',
  'role': '角色权限',
  'config': '系统配置',
  'log': '日志审计',
  'category': '分类管理',
  'reservation': '预约管理',
  'fine': '罚款管理',
  'purchase': '荐购管理',
  'reader_card': '读者证管理',
  'statistics': '统计分析'
}

const PERMISSION_LABEL_MAP = {
  'dashboard:read': '查看运营看板',
  'book:create': '添加图书', 'book:read': '查看图书', 'book:update': '编辑图书', 'book:delete': '删除图书',
  'borrow:create': '办理借阅', 'borrow:read': '查看借阅', 'borrow:return': '办理还书', 'borrow:renew': '办理续借', 'borrow:approve': '借阅审批',
  'user:create': '创建用户', 'user:read': '查看用户', 'user:update': '编辑用户', 'user:delete': '删除用户', 'user:suspend': '禁用用户',
  'role:create': '创建角色', 'role:read': '查看角色', 'role:update': '编辑角色', 'role:delete': '删除角色',
  'config:read': '查看配置', 'config:update': '修改配置',
  'log:read': '查看日志', 'log:export': '导出日志',
  'category:create': '创建分类', 'category:read': '查看分类', 'category:update': '编辑分类', 'category:delete': '删除分类',
  'reservation:create': '创建预约', 'reservation:read': '查看预约', 'reservation:update': '管理预约', 'reservation:cancel': '取消预约',
  'fine:read': '查看罚款', 'fine:update': '管理罚款',
  'purchase:read': '查看荐购', 'purchase:review': '审核荐购',
  'reader_card:issue': '办理读者证', 'reader_card:loss': '挂失读者证', 'reader_card:replace': '补换读者证', 'reader_card:read': '查看读者证',
  'statistics:read': '查看统计分析', 'statistics:export': '导出统计报表'
}

const formatPermissionLabel = (perm) => PERMISSION_LABEL_MAP[perm] || perm

const permissionGroups = computed(() => {
  const groups = {}
  allPermissions.value.forEach(perm => {
    const prefix = perm.split(':')[0]
    if (!groups[prefix]) {
      groups[prefix] = {
        name: prefix,
        label: PERMISSION_GROUP_MAP[prefix] || prefix,
        permissions: []
      }
    }
    groups[prefix].permissions.push(perm)
  })
  return Object.values(groups)
})

const isGroupAllChecked = (group) => {
  return group.permissions.every(p => editForm.permissions.includes(p))
}

const isGroupIndeterminate = (group) => {
  const checkedCount = group.permissions.filter(p => editForm.permissions.includes(p)).length
  return checkedCount > 0 && checkedCount < group.permissions.length
}

const toggleGroup = (group, checked) => {
  if (checked) {
    group.permissions.forEach(p => {
      if (!editForm.permissions.includes(p)) editForm.permissions.push(p)
    })
  } else {
    editForm.permissions = editForm.permissions.filter(p => !group.permissions.includes(p))
  }
}

const fetchRoles = async () => {
  loading.value = true
  try {
    const res = await request.get('/roles')
    roles.value = res.data.items
    allPermissions.value = res.data.all_permissions || []
    defaultPermissions.value = res.data.default_permissions || {}
  } catch (error) {
    console.error('获取角色列表失败:', error)
  } finally {
    loading.value = false
  }
}

const showEditDialog = (row) => {
  selectedRole.value = row
  editForm.role_name = row.role_name
  editForm.description = row.description || ''
  editForm.permissions = [...(row.permissions || [])]
}

const savePermissions = async () => {
  saveLoading.value = true
  try {
    await request.put(`/roles/${selectedRole.value.role_id}`, {
      role_name: editForm.role_name,
      description: editForm.description,
      permissions: editForm.permissions
    })
    ElMessage.success('权限配置已保存')
    await fetchRoles()
    selectedRole.value = null
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saveLoading.value = false
  }
}

const showCreateDialog = () => {
  createForm.role_name = ''
  createForm.description = ''
  createDialogVisible.value = true
}

const createRole = async () => {
  if (!createForm.role_name) {
    ElMessage.warning('请输入角色名称')
    return
  }
  createLoading.value = true
  try {
    await request.post('/roles', {
      role_name: createForm.role_name,
      description: createForm.description,
      permissions: []
    })
    ElMessage.success('角色创建成功')
    createDialogVisible.value = false
    await fetchRoles()
  } catch (error) {
    console.error('创建失败:', error)
  } finally {
    createLoading.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除角色「${row.role_name}」吗？此操作不可恢复。`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await request.delete(`/roles/${row.role_id}`)
    ElMessage.success('角色已删除')
    if (selectedRole.value?.role_id === row.role_id) selectedRole.value = null
    await fetchRoles()
  } catch (error) {
    if (error !== 'cancel') console.error('删除失败:', error)
  }
}

const initDefaultRoles = async () => {
  try {
    await ElMessageBox.confirm(
      '将使用默认权限配置初始化系统角色，已存在的角色权限将被更新。是否继续？',
      '初始化默认角色',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    initLoading.value = true
    const res = await request.get('/roles/init/default-roles')
    ElMessage.success(res.message)
    await fetchRoles()
  } catch (error) {
    if (error !== 'cancel') console.error('初始化失败:', error)
  } finally {
    initLoading.value = false
  }
}

onMounted(() => {
  fetchRoles()
})
</script>

<style scoped lang="scss">
.role-manage {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .title {
      font-size: 16px;
      font-weight: 600;
    }
    .actions {
      display: flex;
      gap: 8px;
    }
  }

  .permission-groups {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .permission-group {
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 16px;

    .group-header {
      margin-bottom: 8px;
      padding-bottom: 8px;
      border-bottom: 1px solid #f0f0f0;
    }

    .group-items {
      padding-left: 24px;
    }

    .perm-checkbox {
      margin-right: 16px;
      margin-bottom: 8px;
    }
  }
}
</style>
