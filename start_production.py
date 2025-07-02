#!/usr/bin/env python3
"""
政策匹配系统 - 生产环境启动脚本
统一API服务，支持自然语言查询和一键匹配功能
"""

import os
import sys
import subprocess
import time
import threading
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """检查系统依赖"""
    logger.info("检查系统依赖...")
    
    # 检查Python包
    required_packages = [
        'fastapi', 'uvicorn', 'numpy', 'sentence_transformers',
        'torch', 'requests', 'pymilvus', 'pydantic'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'fastapi':
                import fastapi
            elif package == 'uvicorn':
                import uvicorn
            elif package == 'pydantic':
                import pydantic
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"缺少必需的Python包: {missing_packages}")
        logger.info("请运行: pip install -r requirements.txt")
        return False
    
    # 检查必需文件
    required_files = [
        'api.py', 'policy_matcher.py', 'models.py',
        'config.py', 'embeddings.py', 'main.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"缺少必需的文件: {missing_files}")
        return False
    
    logger.info("依赖检查通过")
    return True

def check_vector_store():
    """检查向量存储服务"""
    logger.info("检查向量存储服务...")
    try:
        from vector_store import get_vector_store
        vector_store = get_vector_store()
        # 简单的连接测试
        logger.info("向量存储服务连接正常")
        return True
    except Exception as e:
        logger.warning(f"向量存储服务检查失败: {e}")
        return False

def wait_for_service(url, service_name, timeout=30):
    """等待服务启动"""
    import requests
    
    logger.info(f"等待{service_name}启动...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info(f"{service_name}启动成功")
                return True
        except:
            pass
        time.sleep(2)
    
    logger.error(f"{service_name}启动超时")
    return False

def test_api_endpoints():
    """测试API接口"""
    import requests
    import json
    
    logger.info("测试API接口...")
    
    base_url = "http://localhost:8000"
    
    # 测试健康检查
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            logger.info("✅ 健康检查接口正常")
        else:
            logger.warning("⚠️  健康检查接口异常")
    except Exception as e:
        logger.error(f"❌ 健康检查接口测试失败: {e}")
    
    # 测试配置接口
    try:
        response = requests.get(f"{base_url}/config")
        if response.status_code == 200:
            logger.info("✅ 配置接口正常")
        else:
            logger.warning("⚠️  配置接口异常")
    except Exception as e:
        logger.error(f"❌ 配置接口测试失败: {e}")
    
    # 测试基础匹配接口
    try:
        test_data = {
            "industry": "生物医药（含医疗器械）",
            "company_scale": "初创企业（成立<3年，员工<20人）",
            "demand_type": "资金补贴（如研发费用补助）"
        }
        
        response = requests.post(
            f"{base_url}/basic-match",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ 基础匹配接口正常，返回{result.get('total_results', 0)}个结果")
        else:
            logger.warning("⚠️  基础匹配接口异常")
    except Exception as e:
        logger.error(f"❌ 基础匹配接口测试失败: {e}")
    
    # 测试自然语言查询接口
    try:
        test_data = {
            "query": "生物医药相关政策",
            "top_k": 3
        }
        
        response = requests.post(
            f"{base_url}/search",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ 自然语言查询接口正常，返回{result.get('total_results', 0)}个结果")
        else:
            logger.warning("⚠️  自然语言查询接口异常")
    except Exception as e:
        logger.error(f"❌ 自然语言查询接口测试失败: {e}")

def main():
    """主启动函数"""
    print("🚀 政策匹配系统 - 生产环境启动")
    print("=" * 50)
    
    # 1. 检查依赖
    if not check_dependencies():
        logger.error("依赖检查失败，启动终止")
        sys.exit(1)
    
    # 2. 检查向量存储
    if not check_vector_store():
        logger.warning("向量存储服务不可用，部分功能可能受限")
    
    print("\n📋 服务配置:")
    print("  - 统一API服务: http://localhost:8000")
    print("  - API文档: http://localhost:8000/docs")
    print("  - 自然语言查询: ✅")
    print("  - 一键匹配功能: ✅")
    print("  - 智能查询理解: ✅")
    print("  - 企业信息分析: ✅")
    
    try:
        # 3. 启动服务
        logger.info("开始启动API服务...")
        
        # 直接启动主API服务
        import subprocess
        import sys
        
        # 使用subprocess启动服务，这样可以更好地控制进程
        process = subprocess.Popen([
            sys.executable, "api.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # 等待服务启动
        time.sleep(10)
        
        # 4. 验证服务状态
        logger.info("验证服务状态...")
        
        api_ok = wait_for_service("http://localhost:8000/health", "API服务")
        
        if api_ok:
            print("\n🎉 系统启动成功！")
            print("\n📝 API接口:")
            print("  自然语言查询:")
            print("    - 智能搜索: POST http://localhost:8000/search")
            print("    - 快速查询: GET http://localhost:8000/search/quick")
            print("  一键匹配:")
            print("    - 基础匹配: POST http://localhost:8000/basic-match")
            print("    - 精准匹配: POST http://localhost:8000/precise-match")
            print("  系统管理:")
            print("    - 配置查询: GET http://localhost:8000/config")
            print("    - 健康检查: GET http://localhost:8000/health")
            print("    - 系统状态: GET http://localhost:8000/status")
            print("    - 企业信息: GET http://localhost:8000/company-info/{company_name}")
            
            print("\n🔧 测试和文档:")
            print("  - API文档: http://localhost:8000/docs")
            print("  - 查询示例: GET http://localhost:8000/examples")
            print("  - 政策分类: GET http://localhost:8000/categories")
            
            print("\n🧪 快速测试:")
            test_api_endpoints()
            
            print("\n✨ 系统已就绪，按Ctrl+C停止服务")
            
            # 保持进程运行
            try:
                process.wait()
            except KeyboardInterrupt:
                logger.info("收到停止信号，正在关闭服务...")
                process.terminate()
                process.wait()
                logger.info("服务已停止")
        
        else:
            logger.error("服务启动失败")
            process.terminate()
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"启动过程中出现错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 