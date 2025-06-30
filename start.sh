#!/bin/bash

# 政策匹配RAG检索系统启动脚本

echo "=============================================="
echo "政策匹配RAG检索系统"
echo "=============================================="
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

echo "✅ Python3 环境检查通过"

# 检查依赖文件
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt 文件不存在"
    exit 1
fi

echo "✅ 依赖文件检查通过"

# 询问用户选择启动模式
echo ""
echo "请选择启动模式："
echo "1. 基础演示 (无需外部依赖)"
echo "2. 完整系统 (需要Milvus和Elasticsearch)"
echo "3. 安装依赖"
echo ""
read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🚀 启动基础演示模式..."
        echo "此模式展示核心功能，无需外部数据库"
        echo ""
        python3 test_demo.py
        ;;
    2)
        echo ""
        echo "🚀 启动完整系统..."
        echo "请确保Milvus和Elasticsearch已启动"
        echo ""
        
        # 检查端口是否可用
        if command -v nc &> /dev/null; then
            if ! nc -z localhost 19530 2>/dev/null; then
                echo "⚠️  Milvus (端口19530) 未启动，系统将使用备用模式"
            else
                echo "✅ Milvus 连接正常"
            fi
            
            if ! nc -z localhost 9200 2>/dev/null; then
                echo "⚠️  Elasticsearch (端口9200) 未启动，系统将使用备用模式"
            else
                echo "✅ Elasticsearch 连接正常"
            fi
        fi
        
        echo ""
        echo "启动中，请稍候..."
        python3 main.py
        ;;
    3)
        echo ""
        echo "📦 安装依赖包..."
        
        # 检查pip
        if ! command -v pip3 &> /dev/null; then
            echo "❌ pip3 未安装，请先安装pip3"
            exit 1
        fi
        
        # 升级pip
        python3 -m pip install --upgrade pip
        
        # 安装依赖
        pip3 install -r requirements.txt
        
        echo "✅ 依赖安装完成"
        echo ""
        echo "现在可以选择启动模式："
        exec "$0"
        ;;
    *)
        echo "❌ 无效选择，退出"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "系统已退出"
echo "==============================================" 