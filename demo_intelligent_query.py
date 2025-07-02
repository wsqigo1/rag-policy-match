#!/usr/bin/env python3
"""
智能查询政策功能演示
展示自然语言查询的完整流程，包括意图识别、实体提取、智能过滤等
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models import QueryRequest
from policy_matcher import get_policy_matcher
from query_understanding import get_query_processor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def demo_query_understanding():
    """演示查询理解功能"""
    print("=" * 80)
    print("🧠 智能查询理解功能演示")
    print("=" * 80)
    
    # 测试查询案例
    test_queries = [
        {
            "query": "我想查找和生物医药相关的政策",
            "description": "行业政策查询",
            "expected_intent": "find_policy",
            "expected_entities": ["生物医药"]
        },
        {
            "query": "我是一家小型初创企业，现阶段有什么政策比较适用",
            "description": "企业规模适用性查询",
            "expected_intent": "check_eligibility", 
            "expected_entities": ["初创企业", "小型企业"]
        },
        {
            "query": "有哪些研发创新方面的资金支持政策",
            "description": "政策类型查询",
            "expected_intent": "get_funding",
            "expected_entities": ["资金支持", "创新支持"]
        },
        {
            "query": "初创公司可以申请什么补贴",
            "description": "简化查询",
            "expected_intent": "find_policy",
            "expected_entities": ["初创企业"]
        },
        {
            "query": "我们是大型制造企业，想了解产业升级政策的申请条件",
            "description": "复杂查询",
            "expected_intent": "get_requirements",
            "expected_entities": ["大型企业", "制造业"]
        }
    ]
    
    query_processor = get_query_processor()
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📝 测试案例 {i}: {test_case['description']}")
        print(f"   查询: \"{test_case['query']}\"")
        
        # 执行查询理解
        understanding = query_processor.process_query(test_case['query'])
        
        # 显示理解结果
        print(f"\n🎯 理解结果:")
        print(f"   主要意图: {understanding.primary_intent.intent_type} (置信度: {understanding.primary_intent.confidence:.2f})")
        
        if understanding.entities.industries:
            print(f"   识别行业: {understanding.entities.industries}")
        
        if understanding.entities.enterprise_scales:
            print(f"   企业规模: {understanding.entities.enterprise_scales}")
        
        if understanding.entities.policy_types:
            print(f"   政策类型: {understanding.entities.policy_types}")
        
        if understanding.entities.amount_requirements:
            print(f"   金额要求: {understanding.entities.amount_requirements}")
        
        print(f"   查询复杂度: {understanding.query_complexity}")
        print(f"   处理后查询: \"{understanding.processed_query}\"")
        
        # 显示智能过滤
        if understanding.filters:
            print(f"\n🔍 智能过滤规则:")
            for filter_key, filter_value in understanding.filters.items():
                if filter_key == 'prefer_startup_friendly':
                    print(f"   ✅ 偏好初创企业友好政策")
                elif filter_key == 'exclude_high_barrier':
                    print(f"   🚫 排除高门槛政策")
                else:
                    print(f"   • {filter_key}: {filter_value}")
        
        # 显示自然语言上下文
        print(f"\n💭 理解上下文: {understanding.natural_language_context}")
        
        # 验证预期结果
        intent_correct = understanding.primary_intent.intent_type == test_case['expected_intent']
        print(f"\n✅ 意图识别: {'正确' if intent_correct else '不匹配'}")

def demo_intelligent_filtering():
    """演示智能过滤功能"""
    print("\n" + "=" * 80)
    print("🔍 智能过滤功能演示")
    print("=" * 80)
    
    # 模拟政策数据（增强版）
    mock_policies = [
        {
            "id": "policy_001",
            "title": "生物医药产业发展扶持政策",
            "content": "支持生物医药企业发展，给予最高200万元资金支持。适用于各类规模企业。",
            "industries": ["生物医药"],
            "scales": ["初创企业", "中小企业", "大型企业"],
            "types": ["资金支持"],
            "barriers": "低"
        },
        {
            "id": "policy_002", 
            "title": "高新技术企业认定管理办法",
            "content": "企业成立满一年以上，具有自主知识产权，可申请高新技术企业认定。",
            "industries": ["新一代信息技术", "生物医药", "新材料"],
            "scales": ["中小企业", "大型企业"],
            "types": ["资质认定"],
            "barriers": "中"
        },
        {
            "id": "policy_003",
            "title": "大型企业技术改造专项基金",
            "content": "支持年营收5000万以上的大型企业进行技术改造，最高给予1000万元支持。",
            "industries": ["智能制造", "新材料"],
            "scales": ["大型企业"],
            "types": ["资金支持"],
            "barriers": "高"
        },
        {
            "id": "policy_004",
            "title": "初创企业扶持专项基金", 
            "content": "专门针对成立3年内的初创企业，提供最高50万元无息贷款。门槛低，申请简便。",
            "industries": ["通用"],
            "scales": ["初创企业"],
            "types": ["资金支持"],
            "barriers": "低"
        },
        {
            "id": "policy_005",
            "title": "人才引进住房补贴政策",
            "content": "为企业引进的高层次人才提供住房补贴，每人每年最高12万元。",
            "industries": ["通用"],
            "scales": ["中小企业", "大型企业"],
            "types": ["人才政策"],
            "barriers": "中"
        }
    ]
    
    # 测试查询案例
    filter_test_cases = [
        {
            "query": "我是一家小型初创企业，现阶段有什么政策比较适用",
            "description": "初创企业智能过滤",
            "expected_results": ["policy_001", "policy_004"],  # 应该排除高门槛政策
            "excluded_results": ["policy_003"]  # 大型企业专项基金应该被排除
        },
        {
            "query": "我想查找和生物医药相关的政策",
            "description": "行业过滤",
            "expected_results": ["policy_001", "policy_002"],
            "excluded_results": ["policy_003"]
        },
        {
            "query": "有哪些研发创新方面的资金支持政策",
            "description": "政策类型过滤",
            "expected_results": ["policy_001", "policy_003", "policy_004"],
            "excluded_results": ["policy_005"]
        }
    ]
    
    query_processor = get_query_processor()
    
    for i, test_case in enumerate(filter_test_cases, 1):
        print(f"\n🧪 过滤测试 {i}: {test_case['description']}")
        print(f"   查询: \"{test_case['query']}\"")
        
        # 执行查询理解
        understanding = query_processor.process_query(test_case['query'])
        
        # 应用智能过滤
        filtered_policies = []
        
        for policy in mock_policies:
            match = True
            score = 0.0
            reasons = []
            
            # 应用智能过滤规则
            filters = understanding.filters
            
            # 行业过滤
            if 'industries' in filters:
                industry_match = any(
                    industry in policy['industries'] or policy['industries'] == ['通用']
                    for industry in filters['industries']
                )
                if not industry_match:
                    match = False
                else:
                    score += 0.3
                    reasons.append(f"行业匹配: {filters['industries']}")
            
            # 企业规模过滤
            if 'enterprise_scales' in filters:
                scale_match = any(
                    scale in policy['scales']
                    for scale in filters['enterprise_scales']
                )
                if not scale_match:
                    match = False
                else:
                    score += 0.2
                    reasons.append(f"规模匹配: {filters['enterprise_scales']}")
            
            # 政策类型过滤
            if 'policy_types' in filters:
                type_match = any(
                    ptype in policy['types']
                    for ptype in filters['policy_types']
                )
                if type_match:
                    score += 0.3
                    reasons.append(f"类型匹配: {filters['policy_types']}")
            
            # 初创企业友好过滤
            if filters.get('prefer_startup_friendly'):
                if policy['barriers'] == "低":
                    score += 0.2
                    reasons.append("初创企业友好")
            
            # 排除高门槛政策
            if filters.get('exclude_high_barrier'):
                if policy['barriers'] == "高":
                    match = False
                    reasons.append("排除高门槛政策")
            
            if match and score > 0:
                filtered_policies.append({
                    'policy': policy,
                    'score': score,
                    'reasons': reasons
                })
        
        # 按分数排序
        filtered_policies.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\n📊 过滤结果 ({len(filtered_policies)}个政策):")
        for j, result in enumerate(filtered_policies[:3], 1):
            policy = result['policy']
            print(f"   {j}. {policy['title']}")
            print(f"      评分: {result['score']:.2f}")
            print(f"      原因: {', '.join(result['reasons'])}")
            print(f"      门槛: {policy['barriers']}")
        
        # 验证过滤效果
        result_ids = [r['policy']['id'] for r in filtered_policies]
        
        expected_found = all(pid in result_ids for pid in test_case.get('expected_results', []))
        excluded_success = all(pid not in result_ids for pid in test_case.get('excluded_results', []))
        
        print(f"\n✅ 过滤效果:")
        print(f"   预期结果: {'✓' if expected_found else '✗'}")
        print(f"   排除效果: {'✓' if excluded_success else '✗'}")

def demo_real_query_processing():
    """演示真实查询处理"""
    print("\n" + "=" * 80)
    print("🚀 真实查询处理演示")
    print("=" * 80)
    
    test_queries = [
        "我想查找和生物医药相关的政策",
        "我是一家小型初创企业，现阶段有什么政策比较适用", 
        "有哪些研发创新方面的资金支持政策",
        "初创公司可以申请什么补贴"
    ]
    
    policy_matcher = get_policy_matcher()
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 查询测试 {i}: {query}")
        
        request = QueryRequest(query=query, top_k=5)
        response = policy_matcher.match_policies(request)
        
        print(f"   查询结果: {response.total_results}个")
        print(f"   处理时间: {response.processing_time:.3f}秒")
        
        if response.results:
            print(f"   首个结果: {response.results[0].title}")
            print(f"   相关性分数: {response.results[0].relevance_score:.3f}")
        
        if response.suggestions:
            print(f"   系统建议: {response.suggestions[0]}")

def demo_api_examples():
    """演示API使用示例"""
    print("\n" + "=" * 80)
    print("🌐 智能查询API使用示例")
    print("=" * 80)
    
    print("\n📡 主要查询接口:")
    print("  1. 标准查询: POST /search")
    print("  2. 快速查询: GET /search/quick")
    
    examples = [
        {
            "name": "生物医药政策查询",
            "method": "POST",
            "endpoint": "/search",
            "payload": {
                "query": "我想查找和生物医药相关的政策",
                "top_k": 5
            }
        },
        {
            "name": "初创企业适用性查询",
            "method": "POST", 
            "endpoint": "/search",
            "payload": {
                "query": "我是一家小型初创企业，现阶段有什么政策比较适用",
                "industry": None,
                "enterprise_scale": "初创企业（成立<3年，员工<20人）",
                "top_k": 5
            }
        },
        {
            "name": "资金支持政策查询",
            "method": "GET",
            "endpoint": "/search/quick",
            "params": "q=研发创新资金支持&policy_type=资金支持&top_k=3"
        }
    ]
    
    for example in examples:
        print(f"\n📝 {example['name']}:")
        if example['method'] == 'POST':
            print(f"   {example['method']} {example['endpoint']}")
            print(f"   Payload: {json.dumps(example['payload'], ensure_ascii=False, indent=2)}")
        else:
            print(f"   {example['method']} {example['endpoint']}?{example['params']}")
    
    print("\n📋 响应格式:")
    print("""
    {
      "query": "用户查询文本",
      "total_results": 3,
      "results": [
        {
          "policy_id": "policy_001",
          "title": "政策标题",
          "relevance_score": 0.85,
          "matched_chunks": ["相关内容片段"],
          "summary": "政策摘要",
          "key_points": ["核心要点"],
          "applicability": {
            "行业匹配": "高度匹配",
            "规模匹配": "符合要求"
          },
          "requirements": ["申请条件"],
          "suggestions": ["申请建议"]
        }
      ],
      "processing_time": 0.283,
      "suggestions": ["查询优化建议"]
    }
    """)

def main():
    """主函数"""
    try:
        print("🚀 启动智能查询政策功能演示\n")
        
        # 1. 查询理解演示
        demo_query_understanding()
        
        # 2. 智能过滤演示
        demo_intelligent_filtering()
        
        # 3. 真实查询处理演示
        demo_real_query_processing()
        
        # 4. API使用示例
        demo_api_examples()
        
        print("\n" + "=" * 80)
        print("🎉 智能查询功能演示完成！")
        print("=" * 80)
        
        print(f"\n📊 核心能力总结:")
        print(f"  ✅ 意图识别: 支持find_policy、check_eligibility、get_funding等")
        print(f"  ✅ 实体提取: 自动识别行业、企业规模、政策类型等")
        print(f"  ✅ 智能过滤: 初创企业友好、排除高门槛政策")
        print(f"  ✅ 查询扩展: 基于语义相似性扩展查询")
        print(f"  ✅ 混合检索: 向量搜索 + 关键词搜索")
        print(f"  ✅ 动态权重: 根据查询复杂度调整算法权重")
        
        print(f"\n🎯 智能特性:")
        print(f"  🧠 理解自然语言表达")
        print(f"  🔍 智能过滤不适用政策")
        print(f"  📈 动态评分和排序")
        print(f"  💡 个性化建议生成")
        
        print(f"\n🔗 相关接口:")
        print(f"  • 标准查询: POST http://localhost:8000/search")
        print(f"  • 快速查询: GET http://localhost:8000/search/quick")
        print(f"  • API文档: http://localhost:8000/docs")
        
    except Exception as e:
        logger.error(f"❌ 演示执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 