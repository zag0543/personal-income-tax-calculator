@echo off
REM ============================================
REM 个人所得税计算器 - Windows 一键启动脚本
REM 确保已安装 Python 3.9+
REM ============================================

echo 正在检查依赖...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo 依赖安装失败，请检查 Python 和 pip 是否已安装
    pause
    exit /b 1
)

echo 正在启动个人所得税计算器...
echo 浏览器将自动打开，如未打开请访问 http://localhost:8501
streamlit run app.py
pause
