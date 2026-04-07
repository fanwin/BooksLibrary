# 项目开发指南

## 📁 完整项目结构

```
testing-museum/
├── README.md                      # 项目说明文档
├── start.bat                      # Windows启动脚本
├── start.sh                       # Linux/Mac启动脚本
│
├── backend/                       # 后端项目
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py   # 认证和权限依赖
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py              # API路由注册
│   │   │       ├── auth.py                # 认证接口（登录/注册/刷新token）
│   │   │       ├── books.py               # 图书管理接口
│   │   │       ├── borrows.py             # 借阅管理接口
│   │   │       ├── reservations_fines.py  # 预约和罚款接口
│   │   │       ├── statistics.py          # 统计分析接口
│   │   │       ├── ratings.py             # 图书评分/评论/推荐接口
│   │   │       └── system.py              # 系统管理接口（用户/日志/配置/分类/荐购）
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py          # 应用配置管理
│   │   │   ├── database.py        # 数据库连接
│   │   │   └── security.py        # 密码加密和JWT工具
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── models.py          # 所有数据库模型定义
│   │   │
│   │   └── schemas/
│   │       ├── __init__.py
│   │       └── schemas.py         # Pydantic数据验证模式
│   │
│   ├── main.py                    # FastAPI应用入口
│   ├── init_db.py                 # 数据库初始化脚本
│   ├── requirements.txt           # Python依赖
│   ├── .env.example               # 环境变量示例
│   └── .gitignore
│
└── frontend/                      # 前端项目
    ├── index.html                 # HTML入口
    ├── package.json               # Node依赖
    ├── vite.config.js             # Vite配置
    ├── .gitignore
    │
    └── src/
        ├── main.js                # 应用入口
        ├── App.vue                # 根组件
        │
        ├── assets/
        │   └── styles/
        │       └── global.scss    # 全局样式
        │
        ├── components/
        │   └── Placeholder.vue    # 占位组件
        │
        ├── layouts/
        │   └── MainLayout.vue     # 主布局（侧边栏+顶栏）
        │
        ├── router/
        │   └── index.js           # 路由配置和守卫
        │
        ├── stores/
        │   └── user.js            # 用户状态管理
        │
        ├── utils/
        │   └── request.js         # Axios封装
        │
        └── views/
            ├── Login.vue                   # 登录页
            ├── Register.vue                # 注册页
            ├── Dashboard.vue               # 运营看板
            ├── Profile.vue                 # 个人中心
            │
            ├── books/
            │   ├── BookList.vue            # 图书列表
            │   ├── BookRatingComment.vue   # 图书评分与评论组件
            │   └── RecommendationPanel.vue # 个性化推荐面板
            │
            ├── borrows/
            │   └── BorrowList.vue          # 借阅管理
            │
            ├── reservations/
            │   └── ReservationList.vue     # 预约管理
            │
            ├── fines/
            │   └── FineList.vue            # 罚款管理
            │
            ├── statistics/
            │   └── Statistics.vue          # 统计分析
            │
            ├── users/
            │   └── UserList.vue            # 用户管理
            │
            ├── system/
            │   ├── SystemLogs.vue          # 系统日志
            │   └── CategoryManage.vue      # 分类管理
            │
            └── purchase/
                └── PurchaseRequests.vue    # 荐购管理
```

## 🎯 已完成的功能

### 后端 API (100%)
- ✅ 用户认证（登录/注册/刷新令牌）
- ✅ JWT权限验证
- ✅ RBAC角色权限系统
- ✅ 图书CRUD操作
- ✅ 借阅管理（借书/还书/续借）
- ✅ 预约排队机制
- ✅ 罚款计算和缴纳
- ✅ 统计分析接口
- ✅ 系统日志记录
- ✅ 用户管理
- ✅ 分类管理
- ✅ 荐购管理（读者提交/管理员审核）
- ✅ 图书评分（1-5星，支持修改）
- ✅ 图书评论（发表/管理员审核/回复）
- ✅ 个性化推荐（基于借阅偏好/热门/新书）

### 前端页面 (85%)
- ✅ 登录/注册页面（精美UI）
- ✅ 主布局（侧边栏+顶栏导航）
- ✅ 运营看板（数据统计+ECharts图表）
- ✅ 图书管理（列表/搜索/添加/编辑）
- ✅ 个人中心
- ✅ 借阅管理（借阅/归还/续借/批量借书）
- ✅ 预约管理（预约排队/取书/取消）
- ✅ 罚款管理（缴纳/管理员免除）
- ✅ 统计分析（完整图表）
- ✅ 用户管理（完整CRUD）
- ✅ 系统日志（筛选/查看）
- ✅ 荐购管理（读者提交/管理员审核通过拒绝）
- ✅ 图书推荐（为你推荐/新书上架/热门排行）
- ✅ 图书评分与评论组件

## 🚀 快速启动

### 方式一：使用启动脚本（推荐）

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

### 方式二：手动启动

**后端:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python init_db.py
python main.py
```

**前端:**
```bash
cd frontend
npm install
npm run dev
```

## 📝 开发指南

### 添加新的API端点

1. **创建路由文件** `backend/app/api/v1/your_module.py`
```python
from fastapi import APIRouter, Depends
from app.api.dependencies import require_admin

router = APIRouter(prefix="/your-module", tags=["你的模块"])

@router.get("")
async def get_items():
    return {"message": "Hello"}
```

2. **注册路由** `backend/app/api/v1/router.py`
```python
from app.api.v1.your_module import router as your_module_router

api_router.include_router(your_module_router)
```

3. **添加数据模型** `backend/app/schemas/schemas.py`
```python
class YourModel(BaseModel):
    name: str
    # ...
```

### 添加新的前端页面

1. **创建Vue组件** `frontend/src/views/YourPage.vue`

2. **添加路由** `frontend/src/router/index.js`
```javascript
{
  path: 'your-page',
  name: 'YourPage',
  component: () => import('@/views/YourPage.vue'),
  meta: { title: '你的页面' }
}
```

3. **添加菜单** `frontend/src/layouts/MainLayout.vue`
```vue
<el-menu-item index="/your-page">
  <el-icon><YourIcon /></el-icon>
  <template #title>你的页面</template>
</el-menu-item>
```

## 🎨 UI设计说明

### 配色方案
- 主色调: `#409EFF` (Element Plus默认蓝)
- 成功色: `#67C23A`
- 警告色: `#E6A23C`
- 危险色: `#F56C6C`
- 背景色: `#f5f7fa`
- 侧边栏: `#304156`

### 设计规范
- 卡片圆角: `8px`
- 按钮圆角: `6px`
- 输入框圆角: `6px`
- 阴影: `0 2px 12px 0 rgba(0, 0, 0, 0.1)`
- 过渡动画: `0.3s`

## 🔧 数据库说明

### 核心表
- `users` - 用户表
- `roles` - 角色权限表
- `books` - 图书主表
- `book_copies` - 单册副本表
- `borrow_records` - 借阅记录表
- `reservations` - 预约记录表
- `fines` - 罚款记录表
- `purchase_requests` - 荐购申请表
- `book_ratings` - 图书评分表
- `book_comments` - 图书评论表
- `system_logs` - 系统日志表（只增不改）
- `system_configs` - 系统配置表
- `categories` - 图书分类表
- `holidays` - 节假日表
- `notifications` - 消息通知表

### 切换数据库

**PostgreSQL:**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/library_db
```

**MySQL:**
```env
DATABASE_URL=mysql://user:password@localhost:3306/library_db
```

## 📊 API响应格式

所有API统一返回格式：
```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": "2026-04-06T12:00:00Z"
}
```

分页响应：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "size": 20,
    "pages": 5
  }
}
```

## 🔐 安全特性

1. **密码加密**: BCrypt哈希存储
2. **JWT认证**: Access Token + Refresh Token
3. **密码复杂度**: 大小写+数字+特殊字符≥8位
4. **权限控制**: RBAC模型，细粒度到API端点
5. **操作日志**: 记录所有敏感操作
6. **CORS配置**: 限制跨域访问

## 🐛 调试技巧

### 后端调试
- 访问 Swagger UI: `http://localhost:8000/api/docs`
- 查看所有路由: `http://localhost:8000/api/docs#/`
- 在线测试API接口

### 前端调试
- 打开浏览器开发者工具
- 查看Network标签的API请求
- 查看Console的日志输出

## 📦 部署建议

### 生产环境部署

**后端:**
```bash
# 使用Gunicorn + Uvicorn
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

**前端:**
```bash
npm run build
# 将dist目录部署到Nginx或其他Web服务器
```

**Nginx配置示例:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 💡 下一步开发建议

1. **完善前端页面**: 借阅、预约、罚款等模块的完整实现
2. **邮件通知**: 集成SMTP发送借书/还书/催还通知
3. **Excel导入导出**: 批量导入图书数据
4. **PDF报表**: 生成统计报表
5. **数据备份**: 定时备份数据库
6. **单元测试**: 编写后端API测试
7. **性能优化**: 添加Redis缓存
8. **移动端适配**: 响应式设计优化

## 📞 技术支持

遇到问题？检查以下事项：
1. ✅ Python版本 >= 3.9
2. ✅ Node.js版本 >= 16
3. ✅ 依赖是否完整安装
4. ✅ 数据库是否正确初始化
5. ✅ 端口8000和5173是否被占用

---

**Happy Coding!** 🎉
