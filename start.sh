#!/bin/bash

echo "========================================"
echo "   图书馆管理系统 - 快速启动脚本"
echo "========================================"
echo ""

echo "[1/4] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未检测到Python3，请先安装Python 3.9+"
    exit 1
fi
echo "✅ Python环境正常"

echo ""
echo "[2/4] 初始化后端环境..."
cd backend
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

echo "激活虚拟环境..."
source venv/bin/activate

echo "安装Python依赖..."
pip install -r requirements.txt -q

echo "初始化数据库..."
python init_db.py

echo ""
echo "[3/4] 启动后端服务..."
gnome-terminal -- bash -c "cd backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload; exec bash" &

echo "等待后端启动..."
sleep 5

cd ..

echo ""
echo "[4/4] 启动前端服务..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖（首次运行可能需要几分钟）..."
    npm install
fi

gnome-terminal -- bash -c "cd frontend && npm run dev; exec bash" &

echo ""
echo "========================================"
echo "✅ 系统启动完成！"
echo "========================================"
echo ""
echo "后端服务: http://localhost:8000"
echo "API文档:  http://localhost:8000/api/docs"
echo "前端服务: http://localhost:5173"
echo ""
echo "默认账户:"
echo "  超级管理员: admin / Admin@123456"
echo "  读者账户: reader / Reader@123"
echo ""
