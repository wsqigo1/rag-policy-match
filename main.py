#!/usr/bin/env python3
"""
政策匹配RAG检索系统主启动文件
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('policy_matcher.log')
    ]
)

logger = logging.getLogger(__name__)

def get_policy_matcher():
    """获取policy_matcher实例"""
    from policy_matcher import policy_matcher
    return policy_matcher

async def initialize_system():
    """初始化系统"""
    logger.info("正在初始化政策匹配系统...")
    
    try:
        # 获取policy_matcher实例
        policy_matcher = get_policy_matcher()
        
        # 检查系统状态
        status = policy_matcher.get_system_status()
        logger.info(f"系统状态: {status}")
        
        # 如果存在政策文档，自动加载
        pdf_file = "北京市产业政策导引.pdf"
        if os.path.exists(pdf_file):
            logger.info(f"发现政策文档: {pdf_file}，开始加载...")
            success = policy_matcher.add_policy_document(pdf_file)
            if success:
                logger.info("政策文档加载成功")
            else:
                logger.warning("政策文档加载失败")
        else:
            logger.warning(f"未找到政策文档: {pdf_file}")
        
        logger.info("系统初始化完成")
        
    except Exception as e:
        logger.error(f"系统初始化失败: {e}")
        raise e

def run_test_queries():
    """运行测试查询"""
    logger.info("开始测试查询...")
    
    test_queries = [
        {
            "query": "我想查找和生物医药相关的政策",
            "description": "生物医药行业政策查询"
        },
        {
            "query": "我是一家小型初创企业，现阶段有什么政策比较适用",
            "description": "初创企业政策查询"
        },
        {
            "query": "有哪些研发创新方面的资金支持政策",
            "description": "创新资金政策查询"
        }
    ]
    
    from models import QueryRequest
    policy_matcher = get_policy_matcher()
    
    for i, test_case in enumerate(test_queries, 1):
        try:
            logger.info(f"\n=== 测试查询 {i}: {test_case['description']} ===")
            logger.info(f"查询: {test_case['query']}")
            
            query_request = QueryRequest(
                query=test_case['query'],
                top_k=5
            )
            
            response = policy_matcher.match_policies(query_request)
            
            logger.info(f"查询结果: 找到 {response.total_results} 个匹配政策")
            logger.info(f"处理时间: {response.processing_time:.2f}秒")
            
            for j, result in enumerate(response.results, 1):
                logger.info(f"  {j}. {result.title}")
                logger.info(f"     相关性: {result.relevance_score:.3f}")
                logger.info(f"     摘要: {result.summary[:100]}...")
                
            if response.suggestions:
                logger.info("建议:")
                for suggestion in response.suggestions:
                    logger.info(f"  - {suggestion}")
            
        except Exception as e:
            logger.error(f"测试查询 {i} 失败: {e}")

def main():
    """主函数"""
    try:
        logger.info("启动政策匹配RAG检索系统")
        
        # 初始化系统
        asyncio.run(initialize_system())
        
        # 运行测试查询
        run_test_queries()
        
        # 启动API服务
        logger.info("启动API服务...")
        import uvicorn
        from api import app
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭系统...")
    except Exception as e:
        logger.error(f"系统运行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 