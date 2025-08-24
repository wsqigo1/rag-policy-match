#!/usr/bin/env python3
"""
快速向量存储状态检查
用于线上环境的快速状态验证
"""

import os
import socket
import sys

def quick_check():
    """快速检查"""
    print("🔍 快速状态检查")
    
    # 环境变量
    milvus_host = os.getenv('MILVUS_HOST', 'localhost')
    es_host = os.getenv('ES_HOST', 'localhost')
    
    print(f"Milvus: {milvus_host}:19530", end=" ")
    try:
        sock = socket.create_connection((milvus_host, 19530), 3)
        sock.close()
        print("✅")
        milvus_ok = True
    except:
        print("❌")
        milvus_ok = False
    
    print(f"ES: {es_host}:9200", end=" ")
    try:
        sock = socket.create_connection((es_host, 9200), 3)
        sock.close()
        print("✅")
        es_ok = True
    except:
        print("❌")
        es_ok = False
    
    if milvus_ok and es_ok:
        print("🎉 向量存储服务正常")
        sys.exit(0)
    else:
        print("❌ 向量存储服务异常")
        sys.exit(1)

if __name__ == "__main__":
    quick_check()

