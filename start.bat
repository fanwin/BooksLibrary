@echo off
chcp 65001 >nul
echo ========================================
echo    图书馆管理系统 - 快速启动脚本
echo ========================================
echo.

echo [1/4] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到Python，请先安装Python 3.9+
    pause
    exit /b 1
)
echo ✅ Python环境正常

echo.
echo [2/4] 初始化后端环境...
cd backend
if not exist "venv" (
    echo 创建Python虚拟环境...
    python -m venv venv
)

echo 激活虚拟环境...
call venv\Scripts\activate.bat

echo 安装Python依赖...
pip install -r requirements.txt -q

echo 初始化数据库...
python init_db.py

echo.
echo [3/4] 启动后端服务...
start "图书馆管理系统-后端" cmd /k "cd backend && venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo 等待后端启动...
timeout /t 5 /nobreak >nul

cd ..

echo.
echo [4/4] 启动前端服务...
cd frontend
if not exist "node_modules" (
    echo 安装前端依赖（首次运行可能需要几分钟）...
    call npm install
)

start "图书馆管理系统-前端" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo ✅ 系统启动完成！
echo ========================================
echo.
echo 后端服务: http://localhost:8000
echo API文档:  http://localhost:8000/api/docs
echo 前端服务: http://localhost:5173
echo.
echo 默认账户:
echo   超级管理员: admin / Admin@123456
echo   读者账户: reader / Reader@123
echo.
echo 按任意键退出...
pause >nul
