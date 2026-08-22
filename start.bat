@echo off
rem ===== SITAS 本地启动脚本（答辩演示用）=====
rem 用法：双击运行；启动后浏览器访问 http://127.0.0.1:8000
rem 若 8000 端口被占用，可改 --port 8001

cd /d "%~dp0"

echo [1/2] 初始化演示数据（幂等，已有数据则跳过）...
.venv\Scripts\python.exe -m backend.scripts.init_db

echo [2/2] 启动服务...
echo 浏览器访问 http://127.0.0.1:8000  （Ctrl+C 停止）
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

pause
