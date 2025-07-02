#!/usr/bin/env python3
"""
自测通过率功能演示文件
展示政策申请通过率自测功能的完整使用流程
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
    PolicyEligibilityRequest, CompanyInfo
)
from policy_matcher import get_policy_matcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def demo_eligibility_analysis():
    """演示自测通过率分析功能"""
    print("=" * 80)
    print("🔬 政策申请通过率自测功能演示")
    print("=" * 80)
    
    # 演示企业案例
    demo_company = CompanyInfo(
        company_name="北京某某科技有限公司",
        company_type="有限责任公司",
        registered_capital="500万元",
        establishment_date="2022-01-15",
        registered_address="北京市海淀区中关村",
        business_scope="人工智能技术研发；软件开发；技术咨询服务；计算机系统集成",
        honors_qualifications=["中关村高新技术企业"]
    )
    
    # 补充信息
    additional_info = {
        "rd_expense_ratio": 6.0,      # 研发费用占比6%
        "rd_personnel_ratio": 12.0,   # 研发人员占比12%
        "high_tech_income_ratio": 65.0,  # 高新技术产品收入占比65%
        "has_financial_audit": True,  # 有财务审计报告
        "has_project_plan": True,     # 有项目计划
        "annual_revenue": 1200.0,     # 年营收1200万
        "total_employees": 25,        # 总员工25人
        "rd_employees": 8,           # 研发人员8人
        "patents_count": 2,          # 专利2个
        "software_copyrights_count": 5  # 软著5个
    }
    
    print(f"\n📋 企业基本信息")
    print(f"  • 企业名称: {demo_company.company_name}")
    print(f"  • 注册资本: {demo_company.registered_capital}")
    print(f"  • 成立时间: {demo_company.establishment_date}")
    print(f"  • 经营范围: {demo_company.business_scope}")
    print(f"  • 已有资质: {', '.join(demo_company.honors_qualifications)}")
    
    print(f"\n📊 企业数据指标")
    print(f"  • 研发费用占比: {additional_info['rd_expense_ratio']}%")
    print(f"  • 研发人员占比: {additional_info['rd_personnel_ratio']}%")
    print(f"  • 高新收入占比: {additional_info['high_tech_income_ratio']}%")
    print(f"  • 年营业收入: {additional_info['annual_revenue']}万元")
    print(f"  • 专利数量: {additional_info['patents_count']}个")
    print(f"  • 软著数量: {additional_info['software_copyrights_count']}个")
    
    # 执行自测分析
    print("\n🔍 正在分析申请条件...")
    
    policy_matcher = get_policy_matcher()
    
    request = PolicyEligibilityRequest(
        policy_id="policy_157f44c2",
        company_info=demo_company,
        additional_info=additional_info
    )
    
    response = policy_matcher.analyze_policy_eligibility(request)
    
    # 显示分析结果
    print(f"\n🎯 自测通过率分析结果")
    print(f"  政策名称: {response.policy_name}")
    print(f"  政策类型: {response.policy_type}")
    print(f"  支持内容: {response.support_amount}")
    print(f"  预估通过率: {response.pass_rate}%")
    print(f"  通过率等级: {response.pass_level}")
    print(f"  分析耗时: {response.processing_time:.3f}秒")
    
    # 显示通过率进度条
    progress_bar = "█" * (response.pass_rate // 5) + "░" * (20 - response.pass_rate // 5)
    print(f"\n📈 通过率进度: [{progress_bar}] {response.pass_rate}%")
    
    # 显示条件分析
    print(f"\n✅ 已满足条件 ({len(response.condition_analysis.satisfied_conditions)}个):")
    for i, condition in enumerate(response.condition_analysis.satisfied_conditions, 1):
        print(f"  {i}. {condition.condition}")
        print(f"     💡 {condition.details}")
    
    if response.condition_analysis.pending_conditions:
        print(f"\n⚠️  待完善条件 ({len(response.condition_analysis.pending_conditions)}个):")
        for i, condition in enumerate(response.condition_analysis.pending_conditions, 1):
            print(f"  {i}. {condition.condition}")
            print(f"     📝 {condition.details}")
            print(f"     🎯 重要性: {condition.importance}")
    
    if response.condition_analysis.unknown_conditions:
        print(f"\n❓ 不确定条件 ({len(response.condition_analysis.unknown_conditions)}个):")
        for i, condition in enumerate(response.condition_analysis.unknown_conditions, 1):
            print(f"  {i}. {condition.condition}")
            print(f"     ❔ {condition.details}")
    
    # 显示优化建议
    print(f"\n💡 优化建议:")
    for suggestion in response.suggestions:
        if suggestion.startswith("•"):
            print(f"  {suggestion}")
        else:
            print(f"  {suggestion}")
    
    # 通过率等级说明
    print(f"\n📊 通过率等级说明:")
    print(f"  🟢 高 (≥70%): 条件优秀，申请成功率很高")
    print(f"  🟡 中 (40-69%): 条件良好，需要补强部分条件")  
    print(f"  🔴 低 (<40%): 条件不足，需要重点改进")
    
    return response

def demo_improvement_simulation():
    """演示改进措施的通过率提升效果"""
    print("\n" + "=" * 80)
    print("📈 改进措施效果模拟")
    print("=" * 80)
    
    print("\n🎯 模拟场景：企业完善知识产权后的通过率变化")
    
    # 原始企业信息（缺少知识产权）
    original_company = CompanyInfo(
        company_name="北京某某科技有限公司",
        company_type="有限责任公司",
        registered_capital="500万元",
        establishment_date="2022-01-15",
        registered_address="北京市海淀区中关村",
        business_scope="人工智能技术研发；软件开发；技术咨询服务",
        honors_qualifications=[]  # 暂无资质
    )
    
    original_info = {
        "rd_expense_ratio": 6.0,
        "rd_personnel_ratio": 12.0,
        "high_tech_income_ratio": 65.0,
        "has_financial_audit": True,
        "has_project_plan": True
    }
    
    # 改进后企业信息（获得知识产权）
    improved_company = CompanyInfo(
        company_name="北京某某科技有限公司",
        company_type="有限责任公司",
        registered_capital="500万元",
        establishment_date="2022-01-15",
        registered_address="北京市海淀区中关村",
        business_scope="人工智能技术研发；软件开发；技术咨询服务",
        honors_qualifications=["中关村高新技术企业", "知识产权管理体系认证"]
    )
    
    improved_info = {
        "rd_expense_ratio": 8.0,      # 提升研发费用占比
        "rd_personnel_ratio": 15.0,   # 增加研发人员
        "high_tech_income_ratio": 70.0,  # 提升高新收入占比
        "has_financial_audit": True,
        "has_project_plan": True,
        "patents_count": 3,           # 新增专利
        "software_copyrights_count": 8  # 新增软著
    }
    
    policy_matcher = get_policy_matcher()
    
    # 分析改进前
    print("\n📊 改进前分析:")
    original_request = PolicyEligibilityRequest(
        policy_id="policy_157f44c2",
        company_info=original_company,
        additional_info=original_info
    )
    original_response = policy_matcher.analyze_policy_eligibility(original_request)
    print(f"  通过率: {original_response.pass_rate}% ({original_response.pass_level})")
    print(f"  待完善条件: {len(original_response.condition_analysis.pending_conditions)}个")
    
    # 分析改进后
    print("\n📊 改进后分析:")
    improved_request = PolicyEligibilityRequest(
        policy_id="policy_157f44c2",
        company_info=improved_company,
        additional_info=improved_info
    )
    improved_response = policy_matcher.analyze_policy_eligibility(improved_request)
    print(f"  通过率: {improved_response.pass_rate}% ({improved_response.pass_level})")
    print(f"  待完善条件: {len(improved_response.condition_analysis.pending_conditions)}个")
    
    # 显示提升效果
    improvement = improved_response.pass_rate - original_response.pass_rate
    print(f"\n📈 改进效果:")
    print(f"  通过率提升: +{improvement}%")
    print(f"  等级变化: {original_response.pass_level} → {improved_response.pass_level}")
    
    improvement_items = len(original_response.condition_analysis.pending_conditions) - len(improved_response.condition_analysis.pending_conditions)
    print(f"  完善条件: +{improvement_items}个")

def demo_api_usage():
    """演示API使用方法"""
    print("\n" + "=" * 80)
    print("🌐 API使用演示")
    print("=" * 80)
    
    print("\n📡 主要API接口:")
    print("  1. 自测通过率分析: POST /analyze-eligibility")
    print("  2. 获取模板数据: GET /eligibility-template")
    print("  3. 查询政策条件: GET /policy-conditions/{policy_id}")
    
    print("\n📝 API调用示例:")
    print("""
curl -X POST "http://localhost:8000/analyze-eligibility" \\
  -H "Content-Type: application/json" \\
  -d '{
    "policy_id": "policy_157f44c2",
    "company_info": {
      "company_name": "北京某某科技有限公司",
      "company_type": "有限责任公司",
      "registered_capital": "500万元",
      "establishment_date": "2022-01-15",
      "registered_address": "北京市海淀区中关村",
      "business_scope": "人工智能技术研发；软件开发",
      "honors_qualifications": ["中关村高新技术企业"]
    },
    "additional_info": {
      "rd_expense_ratio": 6.0,
      "rd_personnel_ratio": 12.0,
      "high_tech_income_ratio": 65.0,
      "has_financial_audit": true,
      "has_project_plan": true
    }
  }'
    """)
    
    print("\n📋 响应数据格式:")
    print("""
{
  "policy_id": "policy_157f44c2",
  "policy_name": "北京市高新技术企业认定政策",
  "policy_type": "资质认定",
  "support_amount": "最高500万元资金支持",
  "pass_rate": 43,
  "pass_level": "中",
  "condition_analysis": {
    "satisfied_conditions": [...],
    "pending_conditions": [...],
    "unknown_conditions": [...]
  },
  "suggestions": [...],
  "processing_time": 0.001
}
    """)

def main():
    """主函数"""
    try:
        print("🚀 启动自测通过率功能演示\n")
        
        # 1. 基础功能演示
        response = demo_eligibility_analysis()
        
        # 2. 改进效果模拟
        demo_improvement_simulation()
        
        # 3. API使用说明
        demo_api_usage()
        
        print("\n" + "=" * 80)
        print("🎉 演示完成！")
        print("=" * 80)
        
        print(f"\n📊 本次演示结果总结:")
        print(f"  • 企业名称: 北京某某科技有限公司")
        print(f"  • 申请政策: 北京市高新技术企业认定政策")
        print(f"  • 预估通过率: {response.pass_rate}%")
        print(f"  • 通过率等级: {response.pass_level}")
        print(f"  • 已满足条件: {len(response.condition_analysis.satisfied_conditions)}个")
        print(f"  • 待完善条件: {len(response.condition_analysis.pending_conditions)}个")
        
        print(f"\n🔗 相关链接:")
        print(f"  • API文档: http://localhost:8000/docs")
        print(f"  • 自测接口: http://localhost:8000/analyze-eligibility")
        print(f"  • 模板数据: http://localhost:8000/eligibility-template")
        print(f"  • 政策条件: http://localhost:8000/policy-conditions/policy_157f44c2")
        
        print(f"\n💡 使用建议:")
        print(f"  1. 确保企业基础信息准确完整")
        print(f"  2. 提供真实的财务和研发数据")
        print(f"  3. 根据分析结果针对性改进")
        print(f"  4. 定期重新评估通过率变化")
        
    except Exception as e:
        logger.error(f"❌ 演示执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 