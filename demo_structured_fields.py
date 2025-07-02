#!/usr/bin/env python3
"""
结构化字段优化演示脚本
展示基于政策结构化字段的智能匹配和分析功能
"""

import asyncio
import logging

from models import (
    CompanyInfo, QueryRequest, PolicyEligibilityRequest,
    StructuredPolicy
)
from policy_matcher import EnhancedPolicyMatcher, StructuredFieldMatcher
from document_processor import StructuredPolicyExtractor
from llm_manager import LLMManager
from config import Config

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StructuredFieldsDemo:
    """结构化字段演示"""
    
    def __init__(self):
        self.config = Config()
        self.matcher = EnhancedPolicyMatcher(self.config)
        self.llm_manager = LLMManager()
        self.extractor = StructuredPolicyExtractor()
        
    async def initialize(self):
        """初始化"""
        await self.matcher.initialize()
        
    def create_test_policy(self) -> StructuredPolicy:
        """创建测试政策数据"""
        return StructuredPolicy(
            policy_id="test_policy_001",
            title="北京市先进制造业和现代服务业融合试点企业认定及支持办法",
            
            # 基础信息字段
            basis_document="《北京市先进制造业和现代服务业融合试点企业认定及支持办法（试行）》",
            issuing_agency="北京市发展和改革委员会",
            document_number="京发改〔2023〕7号",
            issue_date="2023-07-05",
            
            # 分类和服务字段
            tool_category="资金支持、政策支持",
            service_object="北京市先进制造业和现代服务业融合试点企业",
            service_content="""
            1. 试点企业经综合评价后可纳入重点支持范围，引进符合条件的毕业生实行计划单列。
            2. 试点企业可纳入北京所市重点企业储备库，为企业提升上市管家式服务，加强专项信贷支持，鼓励银行等金融机构面向市级两业融合试点示范开发专项金融产品。
            3. 对于试点企业在津冀地区的产业链延伸项目，与津冀共同支持项目建设。对于产业链延伸企业在京津冀范围内首次采购供应配套企业产品的，可通过北京市高精尖产业发展资金给予产业强链补链同奖励。
            4. 优先推荐试点企业申报国家级两业融合试点，对两业融合发展成效显著、经验模式典型、带动作用明显的试点示范优先案例以多种形式宣传推广。
            """,
            
            # 条件和流程字段
            condition_requirements="""
            试点企业是指符合北京市两业融合八个重点领域、掌握核心技术、融合发展模式典型的企业，包括领跑型试点企业和成长型试点企业两类。
            
            申报领跑型试点企业，应符合以下条件：
            (1) 年营业收入不低于10亿元，或细分行业市场占有率全国前10名；
            (2) 研发设计、检验检测、数字化运营管理、品牌建设等服务投入占企业总投入比重不低于20%。
            
            申报成长型试点企业，应符合以下条件：
            (1) 获得国家高新技术企业、国家级专精特新"小巨人"企业、北京市"专精特新"中小企业称号之一；
            (2) 近三年营业收入平均增长率不低于20%或利润平均增长率不低于8%；
            (3) 研发设计、检验检测、数字化运营管理、品牌建设等服务投入占企业总投入比重不低于40%。
            """,
            
            service_process="""
            1. 形式审查。由市发展改革委对各区报送的两业融合试点示范申报材料进行形式审查，重点审查申报材料的完整性、方向符合性等，通过形式审查的申报单位进入专家评审环节。
            2. 专家评审。由市发展改革委委托第三方机构对通过形式审查的申报单位开展专家评审，重点审查申报单位基础情况、申报材料的合规情况、试点示范案例的创新性和可行性等，并提出评审意见和推荐名单。
            3. 联席会议议。进入专家推荐名单的申报单位，由市级两业融合发展联席会议进行审议，确定拟认定试点示范单位名单。
            4. 公示和确认。对拟认定试点示范单位名单在市发展改革委网站进行为期5个工作日的公示。公示期满无异议的单位确认为正式试点示范单位并公开发布。
            """,
            
            time_frequency="从2023年7月起",
            contact_info="北京市发展和改革委员会：55590088",
            
            # 解析出的关键信息
            industries=["先进制造业", "现代服务业"],
            enterprise_scales=["大型企业", "中小企业", "专精特新"],
            policy_types=["资金支持", "政策支持"],
            support_amount_range={"min_amount": 100, "max_amount": 1000, "amounts": [500]},
            
            full_content="完整政策内容..."
        )
    
    def create_test_companies(self) -> list[CompanyInfo]:
        """创建测试企业数据"""
        return [
                         # 1. 生物医药初创企业
            CompanyInfo(
                company_name="北京创新生物科技有限公司",
                industry="生物医药",
                scale="初创企业",
                employees=45,
                registered_capital=2000.0,
                annual_revenue=800.0,
                enterprise_type="民营企业",
                location="北京市海淀区",
                established_year=2021,
                company_type="有限责任公司",
                establishment_date="2021-03-15",
                registered_address="北京市海淀区中关村科技园",
                business_scope="生物技术研发、医药技术服务"
            ),
            
            # 2. 制造业成长企业
            CompanyInfo(
                company_name="北京智能制造技术有限公司",
                industry="智能制造",
                scale="成长型企业",
                employees=150,
                registered_capital=5000.0,
                annual_revenue=12000.0,
                enterprise_type="高新技术企业",
                location="北京市朝阳区",
                established_year=2018,
                company_type="股份有限公司",
                establishment_date="2018-06-20",
                registered_address="北京市朝阳区望京工业园",
                business_scope="智能制造设备研发、生产"
            ),
            
            # 3. 大型服务企业
            CompanyInfo(
                company_name="北京现代服务集团有限公司",
                industry="现代服务业",
                scale="大型企业",
                employees=800,
                registered_capital=50000.0,
                annual_revenue=120000.0,
                enterprise_type="国有企业",
                location="北京市西城区",
                established_year=2010,
                company_type="国有独资公司",
                establishment_date="2010-01-10",
                registered_address="北京市西城区金融街",
                business_scope="现代服务业投资、管理"
            )
        ]

    async def demo_structured_extraction(self):
        """演示结构化字段提取"""
        print("\n" + "="*60)
        print("📋 演示1：结构化政策信息提取")
        print("="*60)
        
        # 模拟政策文档内容
        policy_content = """
        北京市先进制造业和现代服务业融合试点企业认定及支持办法
        
        依据文件：《北京市先进制造业和现代服务业融合试点企业认定及支持办法（试行）》
        发文机构：北京市发展和改革委员会
        发文字号：京发改〔2023〕7号
        发布日期：2023-07-05
        工具分类：资金支持、政策支持
        服务对象：北京市先进制造业和现代服务业融合试点企业
        
        服务内容：
        1. 试点企业经综合评价后可纳入重点支持范围
        2. 试点企业可纳入北京所市重点企业储备库
        3. 对于试点企业在津冀地区的产业链延伸项目，与津冀共同支持项目建设
        
        条件要求：
        申报领跑型试点企业，应符合以下条件：
        (1) 年营业收入不低于10亿元，或细分行业市场占有率全国前10名
        
        服务流程：
        1. 形式审查。由市发展改革委对各区报送的申报材料进行形式审查
        2. 专家评审。委托第三方机构开展专家评审
        
        时间/频度：从2023年7月起
        联络方式：北京市发展和改革委员会：55590088
        """
        
        # 提取结构化字段
        extracted_fields = self.extractor.extract_structured_fields(policy_content)
        
        print("📄 原始政策文档片段：")
        print(policy_content[:200] + "...")
        
        print("\n🔍 提取的结构化字段：")
        for field, value in extracted_fields.items():
            if value:
                print(f"  • {field}: {value}")
        
        return extracted_fields

    async def demo_field_matching(self):
        """演示字段级匹配分析"""
        print("\n" + "="*60)
        print("🎯 演示2：结构化字段智能匹配")
        print("="*60)
        
        test_policy = self.create_test_policy()
        test_companies = self.create_test_companies()
        
        field_matcher = StructuredFieldMatcher(self.llm_manager)
        
        for i, company in enumerate(test_companies, 1):
            print(f"\n🏢 测试企业{i}：{company.company_name}")
            print(f"   行业：{company.industry}  规模：{company.scale}")
            print(f"   员工数：{company.employees}  年收入：{company.annual_revenue}万元")
            
            # 计算字段匹配分数
            try:
                field_scores = await field_matcher.calculate_field_match_score(
                    company, test_policy
                )
                
                print(f"\n   📊 字段匹配分数：")
                for field, score in field_scores.items():
                    status = "🟢 高" if score >= 0.7 else "🟡 中" if score >= 0.5 else "🔴 低"
                    print(f"     • {field}: {score:.3f} {status}")
                
                # 计算总分
                total_score = sum(
                    score * field_matcher.field_weights.get(field, 0.1)
                    for field, score in field_scores.items()
                )
                print(f"   🎯 综合匹配分数：{total_score:.3f}")
                
            except Exception as e:
                print(f"   ❌ 字段匹配分析失败：{e}")

    async def demo_enhanced_query(self):
        """演示增强查询功能"""
        print("\n" + "="*60)
        print("🔍 演示3：基于结构化字段的增强查询")
        print("="*60)
        
        test_companies = self.create_test_companies()
        
        # 测试查询
        test_queries = [
            "寻找适合生物医药初创企业的资金支持政策",
            "智能制造企业有什么政策支持",
            "大型服务企业可以申请哪些政策"
        ]
        
        for i, (query, company) in enumerate(zip(test_queries, test_companies), 1):
            print(f"\n🔍 查询{i}：{query}")
            print(f"🏢 企业背景：{company.company_name} ({company.industry})")
            
            try:
                request = QueryRequest(
                    query=query,
                    company_info=company,
                    top_k=3,
                    industry=None,
                    enterprise_scale=None,
                    policy_type=None,
                    region=None
                )
                
                response = await self.matcher.query_policies(request)
                
                print(f"📈 查询分析：{response.query_analysis}")
                print(f"📝 个性化推荐：{response.personalized_summary}")
                print(f"⏱️  处理时间：{response.processing_time:.3f}秒")
                
                if response.results:
                    print(f"📋 找到{len(response.results)}个相关政策：")
                    for j, result in enumerate(response.results[:2], 1):
                        print(f"   {j}. {result.title} (匹配度: {result.score:.3f})")
                        if hasattr(result, 'metadata') and 'field_scores' in result.metadata:
                            print(f"      🎯 字段分析: {result.metadata['field_scores']}")
                
            except Exception as e:
                print(f"   ❌ 查询失败：{e}")

    async def demo_eligibility_analysis(self):
        """演示详细资格分析"""
        print("\n" + "="*60)
        print("📊 演示4：详细资格条件分析")
        print("="*60)
        
        test_policy = self.create_test_policy()
        test_companies = self.create_test_companies()
        
        for i, company in enumerate(test_companies, 1):
            print(f"\n🏢 企业{i}：{company.company_name}")
            print(f"📋 政策：{test_policy.title}")
            
            try:
                request = PolicyEligibilityRequest(
                    policy_id=test_policy.policy_id,
                    company_info=company,
                    target_service_object=None,
                    requested_tool_category=None,
                    preferred_support_amount=None
                )
                
                response = await self.matcher.check_eligibility(request)
                
                print(f"\n📊 资格分析结果：")
                print(f"   🎯 通过率：{response.pass_rate}%")
                print(f"   📈 等级：{response.pass_level}")
                print(f"   🔄 匹配分数：{response.matching_score:.3f}" if response.matching_score else "")
                print(f"   ✅ 可行性：{response.feasibility_assessment}" if response.feasibility_assessment else "")
                print(f"   ⏰ 时间线：{response.timeline_estimate}" if response.timeline_estimate else "")
                
                if response.risk_factors:
                    print(f"   ⚠️  风险因素：")
                    for risk in response.risk_factors:
                        print(f"      • {risk}")
                
                if response.suggestions:
                    print(f"   💡 优化建议：")
                    for suggestion in response.suggestions[:3]:
                        print(f"      • {suggestion}")
                
                # 显示详细条件分析
                if hasattr(response, 'condition_analysis') and response.condition_analysis:
                    print(f"\n   📋 详细条件分析：")
                    
                    # 已满足条件
                    if response.condition_analysis.satisfied_conditions:
                        for condition in response.condition_analysis.satisfied_conditions[:2]:
                            print(f"      ✅ {condition.condition}: {condition.details}")
                    
                    # 待完善条件
                    if response.condition_analysis.pending_conditions:
                        for condition in response.condition_analysis.pending_conditions[:2]:
                            print(f"      ⚠️ {condition.condition}: {condition.details}")
                    
                    # 不确定条件
                    if response.condition_analysis.unknown_conditions:
                        for condition in response.condition_analysis.unknown_conditions[:1]:
                            print(f"      ❓ {condition.condition}: {condition.details}")
                
            except Exception as e:
                print(f"   ❌ 资格分析失败：{e}")

    async def demo_comprehensive_analysis(self):
        """演示综合分析报告"""
        print("\n" + "="*60)
        print("📈 演示5：企业政策匹配综合分析报告")
        print("="*60)
        
        company = self.create_test_companies()[1]  # 选择制造业企业
        test_policy = self.create_test_policy()
        
        print(f"🏢 分析企业：{company.company_name}")
        print(f"   📍 所在行业：{company.industry}")
        print(f"   📏 企业规模：{company.scale}")
        print(f"   👥 员工人数：{company.employees}人")
        print(f"   💰 年营业额：{company.annual_revenue}万元")
        
        print(f"\n📋 目标政策：{test_policy.title}")
        
        # 字段级匹配分析
        field_matcher = StructuredFieldMatcher(self.llm_manager)
        field_scores = await field_matcher.calculate_field_match_score(company, test_policy)
        
        # 资格详细分析
        request = PolicyEligibilityRequest(
            policy_id=test_policy.policy_id,
            company_info=company
        )
        eligibility_response = await self.matcher.check_eligibility(request)
        
        # 生成综合报告
        print(f"\n📊 综合分析报告：")
        print(f"="*50)
        
        print(f"🎯 总体匹配度：{eligibility_response.matching_score:.1%}")
        print(f"📈 申请通过率：{eligibility_response.pass_rate:.1%}")
        print(f"⭐ 推荐等级：{eligibility_response.level}")
        
        print(f"\n📋 字段匹配明细：")
        for field, score in field_scores.items():
            field_name_map = {
                'service_object': '服务对象',
                'tool_category': '工具分类',
                'condition_requirements': '条件要求',
                'service_content': '服务内容',
                'issuing_agency': '发文机构',
                'time_frequency': '时间频度',
                'policy_level': '政策级别'
            }
            field_name = field_name_map.get(field, field)
            weight = field_matcher.field_weights.get(field, 0.1)
            weighted_score = score * weight
            
            status = "🟢 优秀" if score >= 0.8 else "🟡 良好" if score >= 0.6 else "🟠 一般" if score >= 0.4 else "🔴 较差"
            print(f"   • {field_name}: {score:.3f} (权重{weight:.1%}) → {weighted_score:.3f} {status}")
        
        print(f"\n💡 核心建议：")
        print(f"   ✅ 可行性评估：{eligibility_response.feasibility_assessment}")
        print(f"   ⏰ 申请时间线：{eligibility_response.timeline_estimate}")
        
        if eligibility_response.risk_factors:
            print(f"   ⚠️  主要风险：{'; '.join(eligibility_response.risk_factors[:2])}")
        
        if eligibility_response.suggestions:
            print(f"   🚀 行动建议：")
            for i, suggestion in enumerate(eligibility_response.suggestions[:3], 1):
                print(f"      {i}. {suggestion}")

async def main():
    """主演示函数"""
    print("🚀 政策匹配系统 - 结构化字段优化演示")
    print("="*60)
    print("本演示将展示基于政策结构化字段的智能匹配和分析功能")
    
    demo = StructuredFieldsDemo()
    
    try:
        # 初始化
        print("\n⏳ 正在初始化系统...")
        await demo.initialize()
        print("✅ 系统初始化完成")
        
        # 运行各项演示
        await demo.demo_structured_extraction()
        await demo.demo_field_matching()
        await demo.demo_enhanced_query()
        await demo.demo_eligibility_analysis()
        await demo.demo_comprehensive_analysis()
        
        print("\n" + "="*60)
        print("🎉 所有演示完成！")
        print("="*60)
        print("📈 系统优化效果：")
        print("   ✅ 结构化字段提取：支持11个核心政策字段的自动识别")
        print("   ✅ 智能字段匹配：7个维度的精准匹配分析")
        print("   ✅ 个性化推荐：基于企业特征的定制化政策推荐")
        print("   ✅ 详细资格分析：多维度条件分析和改进建议")
        print("   ✅ 风险评估：智能识别申请风险和时间线预测")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 