#!/usr/bin/env python3
"""
生产环境向量存储诊断工具
适用于线上环境的问题排查和状态检查
"""

import os
import sys
import socket
import time
import logging
from datetime import datetime

# 简化日志配置
logging.basicConfig(level=logging.WARNING)  # 减少日志噪音

def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")

def print_section(title):
    """打印分节标题"""
    print(f"\n📋 {title}")
    print("-" * 40)

def check_environment():
    """检查环境配置"""
    print_section("环境配置检查")
    
    config = {
        'MILVUS_HOST': os.getenv('MILVUS_HOST', 'localhost'),
        'MILVUS_PORT': os.getenv('MILVUS_PORT', '19530'),
        'ES_HOST': os.getenv('ES_HOST', 'localhost'), 
        'ES_PORT': os.getenv('ES_PORT', '9200'),
    }
    
    for key, value in config.items():
        print(f"  {key:12s}: {value}")
    
    # 警告默认配置
    warnings = []
    if config['MILVUS_HOST'] == 'localhost':
        warnings.append('MILVUS_HOST使用默认值')
    if config['ES_HOST'] == 'localhost':
        warnings.append('ES_HOST使用默认值')
    
    if warnings:
        print(f"\n⚠️  注意: {', '.join(warnings)}")
        print("   线上环境建议设置实际的服务地址")
    
    return config

def test_connectivity(host, port, service_name, timeout=5):
    """测试网络连通性"""
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        elapsed = time.time() - start_time
        
        if result == 0:
            print(f"  ✅ {service_name:15s} {host}:{port} ({elapsed*1000:.1f}ms)")
            return True
        else:
            print(f"  ❌ {service_name:15s} {host}:{port} (连接失败)")
            return False
    except socket.gaierror as e:
        print(f"  ❌ {service_name:15s} {host}:{port} (域名解析失败: {e})")
        return False
    except Exception as e:
        print(f"  ❌ {service_name:15s} {host}:{port} (错误: {e})")
        return False

def check_network_connectivity(config):
    """检查网络连通性"""
    print_section("网络连通性检查")
    
    milvus_ok = test_connectivity(
        config['MILVUS_HOST'], 
        config['MILVUS_PORT'], 
        'Milvus'
    )
    
    es_ok = test_connectivity(
        config['ES_HOST'], 
        config['ES_PORT'], 
        'Elasticsearch'
    )
    
    return milvus_ok, es_ok

def check_vector_store_detailed():
    """详细检查向量存储服务"""
    print_section("向量存储服务检查")
    
    try:
        # 导入模块
        print("  📦 导入向量存储模块...")
        from vector_store import get_vector_store
        print("  ✅ 模块导入成功")
        
        # 初始化
        print("  🔧 初始化向量存储...")
        start_time = time.time()
        vector_store = get_vector_store()
        init_time = time.time() - start_time
        print(f"  ✅ 初始化完成 ({init_time:.2f}s)")
        
        # 检查连接状态
        milvus_connected = vector_store.milvus.connected
        es_connected = vector_store.elasticsearch.connected
        
        print(f"  📊 Milvus连接状态: {'✅ 已连接' if milvus_connected else '❌ 未连接'}")
        print(f"  📊 Elasticsearch连接状态: {'✅ 已连接' if es_connected else '❌ 未连接'}")
        
        # 服务可用性评估
        if milvus_connected and es_connected:
            print("  🎉 所有向量存储服务正常")
            return "all_ok"
        elif milvus_connected or es_connected:
            print("  ⚠️  部分向量存储服务可用")
            return "partial_ok"
        else:
            print("  ❌ 所有向量存储服务不可用")
            return "all_failed"
            
    except ImportError as e:
        print(f"  ❌ 模块导入失败: {e}")
        return "import_error"
    except Exception as e:
        print(f"  ❌ 检查过程出错: {e}")
        return "runtime_error"

def check_system_resources():
    """检查系统资源"""
    print_section("系统资源检查")
    
    try:
        import psutil
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"  🖥️  CPU使用率: {cpu_percent:.1f}%")
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        print(f"  💾 内存使用: {memory.percent:.1f}% ({memory.used//1024//1024}MB/{memory.total//1024//1024}MB)")
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        print(f"  💿 磁盘使用: {disk.percent:.1f}% ({disk.used//1024//1024//1024}GB/{disk.total//1024//1024//1024}GB)")
        
        return True
    except ImportError:
        print("  ⚠️  psutil未安装，跳过资源检查")
        return False
    except Exception as e:
        print(f"  ❌ 资源检查失败: {e}")
        return False

def generate_diagnosis_report(config, network_status, vector_status):
    """生成诊断报告"""
    print_header("诊断报告")
    
    milvus_network, es_network = network_status
    
    print("📊 状态摘要:")
    print(f"  环境配置:     {'✅ 已设置' if config['MILVUS_HOST'] != 'localhost' else '⚠️  使用默认'}")
    print(f"  Milvus网络:   {'✅ 连通' if milvus_network else '❌ 不通'}")
    print(f"  ES网络:       {'✅ 连通' if es_network else '❌ 不通'}")
    print(f"  向量存储:     {get_status_emoji(vector_status)} {get_status_text(vector_status)}")
    
    # 问题诊断
    print("\n🔍 问题诊断:")
    issues = []
    
    if not milvus_network:
        issues.append("Milvus服务网络不通")
    if not es_network:
        issues.append("Elasticsearch服务网络不通")
    if vector_status == "all_failed":
        issues.append("向量存储服务完全不可用")
    elif vector_status == "partial_ok":
        issues.append("部分向量存储服务不可用")
    
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("  ✅ 未发现明显问题")
    
    # 建议
    print("\n💡 建议:")
    if not milvus_network or not es_network:
        print("  1. 检查服务是否启动")
        print("  2. 验证网络配置和防火墙设置")
        print("  3. 确认环境变量设置正确")
    if vector_status in ["all_failed", "partial_ok"]:
        print("  4. 重启向量存储服务")
        print("  5. 检查服务日志")
    if config['MILVUS_HOST'] == 'localhost':
        print("  6. 设置正确的生产环境地址")

def get_status_emoji(status):
    """获取状态表情"""
    mapping = {
        "all_ok": "✅",
        "partial_ok": "⚠️",
        "all_failed": "❌",
        "import_error": "🚫",
        "runtime_error": "⚡"
    }
    return mapping.get(status, "❓")

def get_status_text(status):
    """获取状态文本"""
    mapping = {
        "all_ok": "正常",
        "partial_ok": "部分可用",
        "all_failed": "不可用",
        "import_error": "模块错误",
        "runtime_error": "运行错误"
    }
    return mapping.get(status, "未知")

def main():
    """主函数"""
    print_header(f"生产环境诊断 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 环境配置检查
    config = check_environment()
    
    # 2. 网络连通性检查
    network_status = check_network_connectivity(config)
    
    # 3. 向量存储服务检查
    vector_status = check_vector_store_detailed()
    
    # 4. 系统资源检查（可选）
    check_system_resources()
    
    # 5. 生成诊断报告
    generate_diagnosis_report(config, network_status, vector_status)
    
    # 6. 返回退出码
    if vector_status == "all_ok":
        print(f"\n🎉 诊断完成: 系统状态正常")
        sys.exit(0)
    elif vector_status == "partial_ok":
        print(f"\n⚠️  诊断完成: 系统部分可用")
        sys.exit(1)
    else:
        print(f"\n❌ 诊断完成: 系统存在问题")
        sys.exit(2)

if __name__ == "__main__":
    main()

