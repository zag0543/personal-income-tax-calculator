#!/bin/bash
# ============================================
# 个人所得税计算器 - Mac 一键启动脚本
# 确保已安装 Python 3.9+
# ============================================

echo "正在检查依赖..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "依赖安装失败，请检查 Python 和 pip 是否已安装"
    read -p "按回车键退出..."
    exit 1
fi

echo "正在启动个人所得税计算器..."
echo "浏览器将自动打开，如未打开请访问 http://localhost:8501"
streamlit run app.py
