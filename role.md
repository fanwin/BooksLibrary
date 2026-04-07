# 权限管理模块说明文档

## 一、概述

本系统采用 **基于角色的访问控制（RBAC）** 模型，通过角色配置来控制不同用户的权限。系统包含 5 个内置角色和 40 个细粒度权限点，超级管理员可通过「权限管理」页面动态调整各角色的权限分配。

## 二、角色定义

| 角色标识 | 角色名称 | 说明 |
|---------|---------|------|
| `super_admin` | 超级管理员 | 拥有所有权限，不可删除 |
| `catalog_admin` | 采编管理员 | 负责图书管理、分类管理、荐购审核 |
| `circulation_admin` | 流通管理员 | 负责借阅、还书、罚款、读者证、预约管理 |
| `reader` | 普通读者 | 仅可查看图书和操作自己的借阅/预约 |
| `auditor` | 审计员 | 负责日志审计、数据查看、系统配置查看 |

## 三、权限清单（共 40 个）

### 运营看板
| 权限标识 | 说明 |
|---------|------|
| `dashboard:read` | 查看运营看板（管理员看到全局数据） |

### 图书管理
| 权限标识 | 说明 |
|---------|------|
| `book:create` | 添加图书 |
| `book:read` | 查看图书 |
| `book:update` | 编辑图书 |
| `book:delete` | 删除图书 |

### 借阅管理
| 权限标识 | 说明 |
|---------|------|
| `borrow:create` | 办理借阅 |
| `borrow:read` | 查看借阅记录 |
| `borrow:return` | 办理还书 |
| `borrow:renew` | 办理续借 |
| `borrow:approve` | 借阅审批 |

### 用户管理
| 权限标识 | 说明 |
|---------|------|
| `user:create` | 创建用户 |
| `user:read` | 查看用户 |
| `user:update` | 编辑用户 |
| `user:delete` | 删除用户 |
| `user:suspend` | 禁用/激活用户 |

### 角色权限
| 权限标识 | 说明 |
|---------|------|
| `role:create` | 创建角色 |
| `role:read` | 查看角色 |
| `role:update` | 编辑角色权限 |
| `role:delete` | 删除角色 |

### 系统配置
| 权限标识 | 说明 |
|---------|------|
| `config:read` | 查看系统配置 |
| `config:update` | 修改系统配置 |

### 日志审计
| 权限标识 | 说明 |
|---------|------|
| `log:read` | 查看审计日志 |
| `log:export` | 导出审计日志 |

### 分类管理
| 权限标识 | 说明 |
|---------|------|
| `category:create` | 创建分类 |
| `category:read` | 查看分类 |
| `category:update` | 编辑分类 |
| `category:delete` | 删除分类 |

### 预约管理
| 权限标识 | 说明 |
|---------|------|
| `reservation:create` | 创建预约 |
| `reservation:read` | 查看预约 |
| `reservation:update` | 管理预约（取书确认等） |
| `reservation:cancel` | 取消预约 |

### 罚款管理
| 权限标识 | 说明 |
|---------|------|
| `fine:read` | 查看罚款 |
| `fine:update` | 管理罚款（缴纳、免除等） |

### 荐购管理
| 权限标识 | 说明 |
|---------|------|
| `purchase:read` | 查看荐购 |
| `purchase:review` | 审核荐购 |

### 读者证管理
| 权限标识 | 说明 |
|---------|------|
| `reader_card:issue` | 办理读者证 |
| `reader_card:loss` | 挂失读者证 |
| `reader_card:replace` | 补换读者证 |
| `reader_card:read` | 查看读者证 |

### 统计分析
| 权限标识 | 说明 |
|---------|------|
| `statistics:read` | 查看统计分析 |
| `statistics:export` | 导出统计报表 |

## 四、各角色默认权限

### super_admin（超级管理员）
拥有全部 40 个权限。

### catalog_admin（采编管理员）
```
dashboard:read,
book:create, book:read, book:update, book:delete,
category:create, category:read, category:update, category:delete,
config:read, log:read,
purchase:read, purchase:review,
statistics:read
```

### circulation_admin（流通管理员）
```
dashboard:read,
borrow:create, borrow:read, borrow:return, borrow:renew, borrow:approve,
user:read, reservation:create, reservation:read, reservation:update, reservation:cancel,
fine:read, fine:update, log:read,
reader_card:issue, reader_card:loss, reader_card:replace, reader_card:read,
statistics:read
```

### reader（普通读者）
```
book:read, category:read,
borrow:read, reservation:create, reservation:read, reservation:cancel
```
> 注：读者无 `dashboard:read` 权限，不能访问全局运营看板。读者登录后默认进入「我的看板」页面，展示个人借阅/逾期/罚款数据，通过独立 API `/statistics/my-dashboard` 获取。

### auditor（审计员）
```
dashboard:read,
log:read, log:export,
user:read, borrow:read, fine:read,
config:read,
statistics:read, statistics:export
```

## 五、各角色可访问的功能模块

| 功能模块 | super_admin | catalog_admin | circulation_admin | reader | auditor |
|---------|:-----------:|:-------------:|:-----------------:|:------:|:-------:|
| 运营看板/我的看板 | ✅（全局） | ✅（全局） | ✅（全局） | ✅（个人） | ✅（全局） |
| 图书管理 | ✅ | ✅（写） | ✅（读） | ✅（读） | ✅（读） |
| 借阅管理 | ✅ | ✅（读） | ✅（全部） | ✅（自己） | ✅（读） |
| 预约管理 | ✅ | ✅（读） | ✅（全部） | ✅（自己） | ✅（读） |
| 罚款管理 | ✅ | ✅（读） | ✅（全部） | ✅（自己） | ✅（读） |
| 统计分析 | ✅ | ✅ | ✅ | ❌ | ✅ |
| 分类管理 | ✅ | ✅（写） | ✅（读） | ✅（读） | ✅（读） |
| 节假日管理 | ✅ | ✅ | ✅ | ❌ | ❌ |
| 系统配置 | ✅ | ✅（读） | ❌ | ❌ | ✅（读） |
| 荐购管理 | ✅ | ✅（审核） | ✅（读） | ✅（自己） | ✅（读） |
| 图书推荐 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 用户管理 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 权限管理 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 系统日志 | ✅ | ✅（读） | ✅（读） | ❌ | ✅（全部） |
| 消息通知 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 个人中心 | ✅ | ✅ | ✅ | ✅ | ✅ |

> 注：运营看板按角色区分展示。管理员/审计员看到全局运营数据（今日借还、逾期、罚款、趋势图等），读者看到个人看板（在借图书、逾期、预约、未缴罚款等）。后端通过不同 API 接口隔离数据：管理员调用 `/statistics/dashboard`（需 admin 权限），读者调用 `/statistics/my-dashboard`（仅需登录）。

## 六、改动文件清单

### 后端改动

| 文件 | 改动内容 |
|------|---------|
| `backend/app/api/dependencies.py` | 新增 `get_user_permissions()`、`require_permission()` 函数 |
| `backend/app/api/v1/auth.py` | `/auth/me` 端点增加返回 `permissions` 权限列表 |
| `backend/app/api/v1/statistics.py` | 新增 `/statistics/my-dashboard` 读者个人看板接口 |
| `backend/app/schemas/schemas.py` | `ALL_PERMISSIONS` 新增 `dashboard:read`、`statistics:read`、`statistics:export`；`DEFAULT_ROLE_PERMISSIONS` 同步更新 |

### 前端改动

| 文件 | 改动内容 |
|------|---------|
| `frontend/src/stores/user.js` | 新增 `permissions` 状态和 `hasPermission()`、`hasAnyPermission()`、`hasAllPermissions()` 方法 |
| `frontend/src/views/system/RoleManage.vue` | **新建** - 权限管理页面，支持角色列表、权限编辑、角色创建/删除；权限分组新增「运营看板」「统计分析」 |
| `frontend/src/directives/permission.js` | **新建** - `v-permission` 自定义指令，按钮级别权限控制 |
| `frontend/src/router/index.js` | 新增 `/roles` 路由，完善各模块的 `roles` 限制 |
| `frontend/src/layouts/MainLayout.vue` | 侧边栏新增「权限管理」菜单项，统计分析增加角色限制，运营看板菜单名称按角色区分 |
| `frontend/src/main.js` | 注册 `v-permission` 自定义指令 |
| `frontend/src/views/Dashboard.vue` | 按角色区分展示内容：管理员看全局运营数据，读者看个人看板（在借/逾期/预约/罚款） |

## 七、使用说明

### 初始化默认角色
首次使用权限管理功能时，需要超级管理员登录后点击「初始化默认角色」按钮，将默认权限写入数据库。

### 修改角色权限
1. 进入「系统管理 > 权限管理」页面
2. 点击角色列表中的「编辑权限」按钮
3. 在权限配置面板中勾选/取消权限
4. 点击「保存修改」

### 创建自定义角色
1. 点击右上角「创建角色」按钮
2. 输入角色名称和描述
3. 创建后点击「编辑权限」配置权限

### 前端按钮级权限控制
在 Vue 模板中使用 `v-permission` 指令：
```html
<!-- 单权限：有 book:create 权限才显示 -->
<el-button v-permission="'book:create'">添加图书</el-button>

<!-- 多权限（任一满足）：有 book:create 或 book:update 才显示 -->
<el-button v-permission="['book:create', 'book:update']">操作</el-button>

<!-- 多权限（全部满足）：必须同时有 book:create 和 book:delete 才显示 -->
<el-button v-permission.all="['book:create', 'book:delete']">批量操作</el-button>
```

### 后端细粒度权限校验
在路由中使用 `require_permission` 依赖：
```python
from app.api.dependencies import require_permission

@router.post("/books", response_model=BookResponse)
async def create_book(
    book_data: BookCreate,
    current_user: User = Depends(require_permission("book:create")),
    db: Session = Depends(get_db)
):
    ...
```

## 八、权限检查流程

```
用户请求 → JWT 解析获取 user_id → 查询用户信息 → 检查账户状态
    ↓
判断角色是否为 super_admin → 是 → 放行
    ↓ 否
查询 Role 表获取权限列表 → 匹配所需权限 → 通过/拒绝
```
