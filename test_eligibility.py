#!/usr/bin/env python3
"""
自测通过率功能测试文件
测试政策申请通过率自测算法
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models import (
    PolicyEligibilityRequest, CompanyInfo, 
    PolicyEligibilityResponse, RequirementStatus, ConditionAnalysis
)
from policy_matcher import get_policy_matcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_eligibility_analysis():
    """测试自测通过率分析功能"""
    logger.info("开始测试自测通过率分析功能...")
    
    # 测试案例1：高新技术企业认定 - 条件较好的企业
    test_case_1 = {
        "name": "高新技术企业认定 - 条件较好",
        "policy_id": "policy_157f44c2",
        "company_info": CompanyInfo(
            company_name="北京智能科技有限公司",
            company_type="有限责任公司",
            registered_capital="500万元",
            establishment_date="2022-01-15",  # 成立满2年
            registered_address="北京市海淀区中关村",
            business_scope="人工智能技术研发；软件开发；技术咨询服务；计算机系统集成",
            honors_qualifications=["中关村高新技术企业", "知识产权管理体系认证"]
        ),
        "additional_info": {
            "rd_expense_ratio": 8.5,      # 研发费用占比8.5%
            "rd_personnel_ratio": 15.0,   # 研发人员占比15%
            "high_tech_income_ratio": 75.0,  # 高新技术产品收入占比75%
            "has_financial_audit": True,  # 有财务审计报告
            "has_project_plan": True,     # 有项目计划
            "annual_revenue": 1200.0,     # 年营收1200万
            "total_employees": 25,        # 总员工25人
            "rd_employees": 8,           # 研发人员8人
            "patents_count": 3,          # 专利3个
            "software_copyrights_count": 5  # 软著5个
        },
        "expected_pass_rate_range": (60, 80)
    }
    
    # 测试案例2：高新技术企业认定 - 条件一般的企业
    test_case_2 = {
        "name": "高新技术企业认定 - 条件一般",
        "policy_id": "policy_157f44c2",
        "company_info": CompanyInfo(
            company_name="北京创新有限公司",
            company_type="有限责任公司",
            registered_capital="300万元",
            establishment_date="2023-06-01",  # 成立不足2年
            registered_address="北京市朝阳区",
            business_scope="软件开发；技术服务",
            honors_qualifications=["科技型中小企业"]
        ),
        "additional_info": {
            "rd_expense_ratio": 3.5,      # 研发费用占比3.5%（不达标）
            "rd_personnel_ratio": 8.0,    # 研发人员占比8%（不达标）
            "high_tech_income_ratio": 45.0,  # 高新技术产品收入占比45%（不达标）
            "has_financial_audit": False, # 无财务审计报告
            "has_project_plan": True,     # 有项目计划
            "annual_revenue": 800.0,      # 年营收800万
            "total_employees": 15,        # 总员工15人
            "rd_employees": 3,           # 研发人员3人
            "patents_count": 0,          # 专利0个
            "software_copyrights_count": 2  # 软著2个
        },
        "expected_pass_rate_range": (20, 40)
    }
    
    # 测试案例3：条件优秀的企业
    test_case_3 = {
        "name": "高新技术企业认定 - 条件优秀",
        "policy_id": "policy_157f44c2",
        "company_info": CompanyInfo(
            company_name="北京顶尖科技有限公司",
            company_type="有限责任公司",
            registered_capital="2000万元",
            establishment_date="2020-03-15",  # 成立满4年
            registered_address="北京市中关村科技园",
            business_scope="人工智能技术研发；大数据分析；云计算服务；软件开发",
            honors_qualifications=["国家高新技术企业", "知识产权贯标企业", "专精特新小巨人"]
        ),
        "additional_info": {
            "rd_expense_ratio": 12.0,     # 研发费用占比12%
            "rd_personnel_ratio": 25.0,   # 研发人员占比25%
            "high_tech_income_ratio": 85.0,  # 高新技术产品收入占比85%
            "has_financial_audit": True,  # 有财务审计报告
            "has_project_plan": True,     # 有项目计划
            "annual_revenue": 5000.0,     # 年营收5000万
            "total_employees": 80,        # 总员工80人
            "rd_employees": 20,          # 研发人员20人
            "patents_count": 15,         # 专利15个
            "software_copyrights_count": 25  # 软著25个
        },
        "expected_pass_rate_range": (80, 95)
    }
    
    test_cases = [test_case_1, test_case_2, test_case_3]
    
    policy_matcher = get_policy_matcher()
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n=== 测试案例 {i}: {test_case['name']} ===")
        
        try:
            # 创建请求
            request = PolicyEligibilityRequest(
                policy_id=test_case['policy_id'],
                company_info=test_case['company_info'],
                additional_info=test_case['additional_info']
            )
            
            # 执行分析
            response = policy_matcher.analyze_policy_eligibility(request)
            
            # 输出结果
            logger.info(f"企业名称: {test_case['company_info'].company_name}")
            logger.info(f"政策名称: {response.policy_name}")
            logger.info(f"政策类型: {response.policy_type}")
            logger.info(f"支持内容: {response.support_amount}")
            logger.info(f"预估通过率: {response.pass_rate}%")
            logger.info(f"通过率等级: {response.pass_level}")
            logger.info(f"分析时间: {response.processing_time:.3f}秒")
            
            # 显示已满足条件
            logger.info(f"\n✅ 已满足条件 ({len(response.condition_analysis.satisfied_conditions)}个):")
            for condition in response.condition_analysis.satisfied_conditions:
                logger.info(f"  • {condition.condition}")
                logger.info(f"    详情: {condition.details}")
            
            # 显示待完善条件
            logger.info(f"\n⚠️  待完善条件 ({len(response.condition_analysis.pending_conditions)}个):")
            for condition in response.condition_analysis.pending_conditions:
                logger.info(f"  • {condition.condition}")
                logger.info(f"    详情: {condition.details}")
                logger.info(f"    重要性: {condition.importance}")
            
            # 显示不确定条件
            if response.condition_analysis.unknown_conditions:
                logger.info(f"\n❓ 不确定条件 ({len(response.condition_analysis.unknown_conditions)}个):")
                for condition in response.condition_analysis.unknown_conditions:
                    logger.info(f"  • {condition.condition}")
                    logger.info(f"    详情: {condition.details}")
            
            # 显示建议
            logger.info("\n💡 优化建议:")
            for suggestion in response.suggestions:
                logger.info(f"  {suggestion}")
            
            # 验证通过率范围
            expected_min, expected_max = test_case['expected_pass_rate_range']
            if expected_min <= response.pass_rate <= expected_max:
                logger.info(f"✅ 通过率 {response.pass_rate}% 在预期范围 [{expected_min}%-{expected_max}%] 内")
            else:
                logger.warning(f"⚠️  通过率 {response.pass_rate}% 超出预期范围 [{expected_min}%-{expected_max}%]")
            
        except Exception as e:
            logger.error(f"❌ 测试案例 {i} 执行失败: {e}")
    
    logger.info("\n=== 自测通过率功能测试完成 ===")

def test_api_integration():
    """测试API集成"""
    logger.info("\n开始测试API集成...")
    
    try:
        import requests
        
        # 测试自测通过率API
        api_url = "http://localhost:8000/analyze-eligibility"
        
        test_request = {
            "policy_id": "policy_157f44c2",
            "company_info": {
                "company_name": "北京测试科技有限公司",
                "company_type": "有限责任公司",
                "registered_capital": "500万元",
                "establishment_date": "2022-01-15",
                "registered_address": "北京市海淀区",
                "business_scope": "软件开发；技术服务",
                "honors_qualifications": ["中关村高新技术企业"]
            },
            "additional_info": {
                "rd_expense_ratio": 6.0,
                "rd_personnel_ratio": 12.0,
                "high_tech_income_ratio": 65.0,
                "has_financial_audit": True,
                "has_project_plan": True
            }
        }
        
        logger.info("发送API请求...")
        response = requests.post(api_url, json=test_request, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ API请求成功")
            logger.info(f"  通过率: {result['pass_rate']}%")
            logger.info(f"  等级: {result['pass_level']}")
            logger.info(f"  已满足条件: {len(result['condition_analysis']['satisfied_conditions'])}个")
            logger.info(f"  待完善条件: {len(result['condition_analysis']['pending_conditions'])}个")
        else:
            logger.error(f"❌ API请求失败: {response.status_code}")
            logger.error(f"响应内容: {response.text}")
    
    except ImportError:
        logger.info("requests库未安装，跳过API集成测试")
    except Exception as e:
        logger.error(f"❌ API集成测试失败: {e}")

def test_edge_cases():
    """测试边界情况"""
    logger.info("\n开始测试边界情况...")
    
    policy_matcher = get_policy_matcher()
    
    # 测试1：刚成立的企业
    logger.info("\n--- 测试边界情况1: 刚成立的企业 ---")
    try:
        request = PolicyEligibilityRequest(
            policy_id="policy_157f44c2",
            company_info=CompanyInfo(
                company_name="北京新成立科技有限公司",
                company_type="有限责任公司",
                registered_capital="100万元",
                establishment_date=datetime.now().strftime("%Y-%m-%d"),  # 今天成立
                registered_address="北京市",
                business_scope="软件开发",
                honors_qualifications=[]
            ),
            additional_info={}
        )
        
        response = policy_matcher.analyze_policy_eligibility(request)
        logger.info(f"刚成立企业通过率: {response.pass_rate}%")
        logger.info(f"待完善条件数量: {len(response.condition_analysis.pending_conditions)}")
        
    except Exception as e:
        logger.error(f"边界测试1失败: {e}")
    
    # 测试2：无效政策ID
    logger.info("\n--- 测试边界情况2: 无效政策ID ---")
    try:
        request = PolicyEligibilityRequest(
            policy_id="invalid_policy_id",
            company_info=CompanyInfo(
                company_name="测试企业",
                company_type="有限责任公司",
                registered_capital="100万元",
                establishment_date="2022-01-01",
                registered_address="北京市",
                business_scope="软件开发",
                honors_qualifications=[]
            ),
            additional_info={}
        )
        
        response = policy_matcher.analyze_policy_eligibility(request)
        logger.info(f"无效政策ID处理结果: 通过率={response.pass_rate}%, 政策名称={response.policy_name}")
        
    except Exception as e:
        logger.info(f"预期的错误处理: {e}")

def main():
    """主函数"""
    try:
        logger.info("🚀 开始自测通过率功能全面测试")
        
        # 1. 基础功能测试
        test_eligibility_analysis()
        
        # 2. 边界情况测试
        test_edge_cases()
        
        # 3. API集成测试
        test_api_integration()
        
        logger.info("\n🎉 所有测试完成！")
        
        # 输出使用说明
        logger.info("\n📖 使用说明:")
        logger.info("1. 直接调用: python test_eligibility.py")
        logger.info("2. API接口: POST http://localhost:8000/analyze-eligibility")
        logger.info("3. 模板获取: GET http://localhost:8000/eligibility-template")
        logger.info("4. 条件查询: GET http://localhost:8000/policy-conditions/{policy_id}")
        
    except Exception as e:
        logger.error(f"❌ 测试执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 