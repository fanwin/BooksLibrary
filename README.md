# 图书馆管理系统

一个现代化的图书馆管理平台，基于 **FastAPI** + **Vue3** + **Element Plus** 构建。

## 📋 项目特性

### 核心功能
- ✅ **用户与权限管理（RBAC）**：支持5种角色（超级管理员、采编管理员、流通管理员、读者、系统审计员）
- ✅ **图书与馆藏管理**：图书编目、分类管理、单册管理、图书盘点
- ✅ **借阅流通管理**：借书、还书、续借、预约排队机制
- ✅ **罚款管理**：自动计算逾期罚款、支持在线缴纳
- ✅ **统计分析**：运营看板、借阅趋势、热门图书、分类分布
- ✅ **荐购管理**：读者荐购、管理员审核
- ✅ **系统日志**：完整的操作日志审计（只增不改）

### 技术栈

#### 后端
- **FastAPI**: 高性能Python Web框架
- **SQLAlchemy**: ORM数据库操作
- **Pydantic**: 数据验证
- **JWT**: 用户认证
- **SQLite**: 默认数据库（可切换PostgreSQL/MySQL）

#### 前端
- **Vue 3**: 渐进式JavaScript框架
- **Vite**: 快速构建工具
- **Element Plus**: 现代化UI组件库
- **Pinia**: 状态管理
- **Vue Router**: 路由管理
- **ECharts**: 数据可视化
- **Axios**: HTTP客户端

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Node.js 16+
- npm 或 yarn

### 后端启动

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境（推荐）
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量（可选）
cp .env.example .env
# 编辑 .env 文件配置数据库等参数

# 6. 初始化数据库
python init_db.py

# 7. 启动服务
python main.py
# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端服务将在 `http://localhost:8000` 启动
- API文档: `http://localhost:8000/api/docs`
- ReDoc文档: `http://localhost:8000/api/redoc`

### 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

前端服务将在 `http://localhost:5173` 启动

## 👤 默认账户

系统初始化后会创建以下默认账户：

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 超级管理员 | admin | Admin@123456 |
| 采编管理员 | catalog_admin | Catalog@123 |
| 流通管理员 | circulation_admin | Circulation@123 |
| 读者 | reader | Reader@123 |

**⚠️ 重要：首次登录后请立即修改默认密码！**

## 📁 项目结构

```
testing-museum/
├── backend/                    # 后端项目
│   ├── app/
│   │   ├── api/               # API路由
│   │   │   └── v1/           # API v1版本
│   │   │       ├── auth.py              # 认证路由
│   │   │       ├── books.py             # 图书管理
│   │   │       ├── borrows.py           # 借阅管理
│   │   │       ├── reservations_fines.py # 预约和罚款
│   │   │       ├── statistics.py        # 统计分析
│   │   │       └── system.py            # 系统管理
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py              # 应用配置
│   │   │   ├── database.py            # 数据库配置
│   │   │   └── security.py            # 安全工具
│   │   ├── models/            # 数据库模型
│   │   │   └── models.py              # 所有模型定义
│   │   └── schemas/           # Pydantic模式
│   │       └── schemas.py             # 数据验证模式
│   ├── main.py                # 应用入口
│   ├── init_db.py             # 数据库初始化
│   └── requirements.txt       # Python依赖
│
└── frontend/                   # 前端项目
    ├── src/
    │   ├── assets/            # 静态资源
    │   ├── layouts/           # 布局组件
    │   ├── router/            # 路由配置
    │   ├── stores/            # Pinia状态管理
    │   ├── utils/             # 工具函数
    │   └── views/             # 页面组件
    ├── package.json
    └── vite.config.js
```

## 🔧 配置说明

### 后端配置（.env）

```env
# 数据库配置
DATABASE_URL=sqlite:///./library_management.db
# PostgreSQL: postgresql://user:password@localhost/dbname
# MySQL: mysql://user:password@localhost/dbname

# JWT配置
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=jwt-secret-key-change-in-production

# 邮件配置（可选）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password

# Redis配置（可选）
REDIS_URL=redis://localhost:6379/0
```

### 前端代理配置

前端已配置API代理，开发时会自动转发到后端：

```javascript
// vite.config.js
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    }
  }
}
```

## 📊 API文档

启动后端服务后，访问以下地址查看完整的API文档：

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

所有API端点都支持在线测试，方便调试。

## 🔐 权限说明

### 角色权限矩阵

| 功能模块 | 超级管理员 | 采编管理员 | 流通管理员 | 读者 | 审计员 |
|---------|-----------|-----------|-----------|------|-------|
| 用户管理 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 图书管理 | ✅ | ✅ | ❌ | 只读 | ❌ |
| 借阅管理 | ✅ | ❌ | ✅ | 自己 | ❌ |
| 预约管理 | ✅ | ❌ | ✅ | 自己 | ❌ |
| 罚款管理 | ✅ | ❌ | ✅ | 自己 | ❌ |
| 统计分析 | ✅ | ❌ | ❌ | ❌ | ✅ |
| 系统日志 | ✅ | ❌ | ❌ | ❌ | ✅ |
| 荐购管理 | ✅ | ✅ | ✅ | 自己 | ❌ |

## 🎨 前端特性

- **响应式设计**：适配不同屏幕尺寸
- **主题定制**：基于Element Plus的主题系统
- **动画效果**：流畅的页面过渡和交互动画
- **数据可视化**：ECharts图表展示统计数据
- **国际化**：支持中文（可扩展其他语言）

## 📝 开发指南

### 添加新的API端点

1. 在 `backend/app/api/v1/` 创建新的路由文件
2. 在 `backend/app/api/v1/router.py` 中注册路由
3. 在 `backend/app/schemas/schemas.py` 添加数据验证模式
4. 在前端创建对应的API调用函数

### 添加新的页面

1. 在 `frontend/src/views/` 创建Vue组件
2. 在 `frontend/src/router/index.js` 添加路由配置
3. 在 `frontend/src/layouts/MainLayout.vue` 添加菜单项（如需要）

## 🐛 常见问题

### 1. 数据库初始化失败
```bash
# 删除旧数据库文件
rm backend/library_management.db
# 重新初始化
python init_db.py
```

### 2. 前端依赖安装失败
```bash
# 清除npm缓存
npm cache clean --force
# 删除node_modules重新安装
rm -rf node_modules
npm install
```

### 3. CORS错误
确保后端 `.env` 文件中的 `ALLOWED_ORIGINS` 包含前端地址：
```env
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

## 🚧 待扩展功能

- [ ] 邮件通知系统
- [ ] 短信通知（预留接口）
- [ ] RFID/条形码扫描
- [ ] Excel批量导入导出
- [ ] PDF报表生成
- [ ] 数据备份与恢复
- [ ] 节假日管理
- [ ] 个性化推荐算法
- [ ] 图书评分与评论

## 📄 License

MIT License

## 👥 联系方式

如有问题或建议，请提交Issue。

---

**祝您使用愉快！** 🎉
