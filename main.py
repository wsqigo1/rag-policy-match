#!/usr/bin/env python3
"""
政策匹配RAG检索系统主启动文件
集成自然语言查询和一键匹配功能
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
    
    # 测试自然语言查询
    natural_language_tests = [
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
    
    from models import QueryRequest, BasicMatchRequest, CompanyInfo, PreciseMatchRequest
    policy_matcher = get_policy_matcher()
    
    # 测试自然语言查询
    logger.info("\n=== 测试自然语言查询功能 ===")
    for i, test_case in enumerate(natural_language_tests, 1):
        try:
            logger.info(f"\n--- 测试 {i}: {test_case['description']} ---")
            logger.info(f"查询: {test_case['query']}")
            
            query_request = QueryRequest(
                query=test_case['query'],
                policy_type=None,
                region=None,
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
            logger.error(f"自然语言测试查询 {i} 失败: {e}")
    
    # 测试基础匹配功能
    logger.info("\n=== 测试基础匹配功能 ===")
    try:
        basic_request = BasicMatchRequest(
            industry="生物医药（含医疗器械）",
            company_scale="初创企业（成立<3年，员工<20人）",
            demand_type="资金补贴（如研发费用补助）"
        )
        
        logger.info(f"基础匹配参数: 行业={basic_request.industry}, 规模={basic_request.company_scale}, 需求={basic_request.demand_type}")
        
        response = policy_matcher.basic_match(basic_request)
        
        logger.info(f"基础匹配结果: 找到 {response.total_results} 个匹配政策")
        logger.info(f"处理时间: {response.processing_time:.2f}秒")
        logger.info(f"匹配类型: {response.match_type}")
        
        for i, match in enumerate(response.matches[:3], 1):
            logger.info(f"  {i}. {match.policy_name}")
            logger.info(f"     匹配度: {match.match_level} ({match.match_score:.3f})")
            logger.info(f"     政策类型: {match.policy_type}")
            logger.info(f"     关键描述: {match.key_description[:100]}...")
        
        if response.suggestions:
            logger.info("建议:")
            for suggestion in response.suggestions:
                logger.info(f"  - {suggestion}")
                
    except Exception as e:
        logger.error(f"基础匹配测试失败: {e}")
    
    # 测试精准匹配功能
    logger.info("\n=== 测试精准匹配功能 ===")
    try:
        company_info = CompanyInfo(
            company_name="北京智能科技有限公司",
            company_type="有限责任公司",
            registered_capital=500.0,  # 修改为数字格式，单位：万元
            establishment_date="2023-01-15",
            registered_address="北京市海淀区中关村",
            business_scope="人工智能技术研发；软件开发；技术咨询服务",
            honors_qualifications=["中关村高新技术企业"]
        )
        
        basic_request = BasicMatchRequest(
            industry="新一代信息技术",
            company_scale="初创企业（成立<3年，员工<20人）",
            demand_type="资质认定（如高新企业、专精特新）"
        )
        
        precise_request = PreciseMatchRequest(
            basic_request=basic_request,
            company_info=company_info
        )
        
        logger.info(f"精准匹配企业: {company_info.company_name}")
        
        response = policy_matcher.precise_match(precise_request)
        
        logger.info(f"精准匹配结果: 找到 {response.total_results} 个匹配政策")
        logger.info(f"处理时间: {response.processing_time:.2f}秒")
        logger.info(f"匹配类型: {response.match_type}")
        
        for i, match in enumerate(response.matches[:3], 1):
            logger.info(f"  {i}. {match.policy_name}")
            logger.info(f"     匹配度: {match.match_level} ({match.match_score:.3f})")
            logger.info(f"     政策类型: {match.policy_type}")
            logger.info(f"     关键描述: {match.key_description[:100]}...")
        
        if response.suggestions:
            logger.info("建议:")
            for suggestion in response.suggestions:
                logger.info(f"  - {suggestion}")
                
    except Exception as e:
        logger.error(f"精准匹配测试失败: {e}")

def main():
    """主函数"""
    try:
        logger.info("启动政策匹配RAG检索系统")
        
        # 初始化系统
        asyncio.run(initialize_system())
        
        # 运行测试查询
        run_test_queries()
        
        # 启动API服务
        logger.info("\n=== 启动FastAPI服务 ===")
        logger.info("服务地址: http://localhost:8000")
        logger.info("API文档: http://localhost:8000/docs")
        logger.info("功能包括:")
        logger.info("  - 自然语言查询: POST /search")
        logger.info("  - 基础匹配: POST /basic-match")
        logger.info("  - 精准匹配: POST /precise-match")
        logger.info("  - 配置查询: GET /config")
        logger.info("  - 健康检查: GET /health")
        
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