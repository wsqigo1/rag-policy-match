#!/usr/bin/env python3
"""
政策匹配系统测试演示脚本 - 统一API版本
展示自然语言查询和一键匹配功能
"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_without_dependencies():
    """不依赖外部服务的基础测试"""
    print("=== 政策匹配系统基础功能测试 ===\n")
    
    try:
        # 测试配置加载
        print("1. 测试配置加载...")
        from config import config
        print(f"   ✓ 嵌入模型: {config.EMBEDDING_MODEL}")
        print(f"   ✓ 最大分块大小: {config.MAX_CHUNK_SIZE}")
        print(f"   ✓ 支持的行业: {list(config.INDUSTRY_MAPPING.keys())}")
        print()
        
        # 测试数据模型
        print("2. 测试数据模型...")
        from models import (
            QueryRequest, PolicyChunk, 
            BasicMatchRequest, PreciseMatchRequest, CompanyInfo
        )
        
        # 创建自然语言查询请求
        query_req = QueryRequest(
            query="生物医药相关政策",
            industry="生物医药（含医疗器械）",
            enterprise_scale="初创企业（成立<3年，员工<20人）",
            policy_type=None,
            region=None,
            top_k=5
        )
        print(f"   ✓ 自然语言查询: {query_req.query}")
        print(f"   ✓ 行业筛选: {query_req.industry}")
        print(f"   ✓ 企业规模: {query_req.enterprise_scale}")
        
        # 创建基础匹配请求
        basic_req = BasicMatchRequest(
            industry="生物医药（含医疗器械）",
            company_scale="初创企业（成立<3年，员工<20人）",
            demand_type="资金补贴（如研发费用补助）"
        )
        print(f"   ✓ 基础匹配请求: {basic_req.industry} | {basic_req.company_scale} | {basic_req.demand_type}")
        
        # 创建企业信息
        company_info = CompanyInfo(
            company_name="北京生物科技有限公司",
            company_type="有限责任公司",
            registered_capital="500万元",
            establishment_date="2023-01-15",
            registered_address="北京市海淀区中关村",
            business_scope="生物技术研发；医疗器械开发",
            honors_qualifications=["中关村高新技术企业"]
        )
        print(f"   ✓ 企业信息: {company_info.company_name} ({company_info.company_type})")
        
        # 创建精准匹配请求
        precise_req = PreciseMatchRequest(
            basic_request=basic_req,
            company_info=company_info
        )
        print(f"   ✓ 精准匹配请求: 企业={precise_req.company_info.company_name}")
        print()
        
        # 测试文档处理
        print("3. 测试文档处理...")
        from document_processor import DocumentProcessor
        processor = DocumentProcessor()
        
        # 如果PDF文件存在，尝试处理
        pdf_file = "北京市产业政策导引.pdf"
        if os.path.exists(pdf_file):
            print(f"   发现政策文档: {pdf_file}")
            try:
                policy_doc = processor.process_document(pdf_file)
                print(f"   ✓ 文档处理成功")
                print(f"   ✓ 政策ID: {policy_doc.policy_id}")
                print(f"   ✓ 标题: {policy_doc.title[:50]}...")
                print(f"   ✓ 分块数量: {len(policy_doc.chunks)}")
                print(f"   ✓ 识别行业: {policy_doc.industry}")
                print(f"   ✓ 企业规模: {policy_doc.enterprise_scale}")
                
                # 显示几个分块示例
                print("   分块示例:")
                for i, chunk in enumerate(policy_doc.chunks[:3]):
                    print(f"     {i+1}. {chunk.content[:100]}...")
                print()
                
            except Exception as e:
                print(f"   ✗ 文档处理失败: {e}")
                print()
        else:
            print(f"   ⚠ 未找到政策文档: {pdf_file}")
            print("   请确保PDF文件在项目根目录")
            print()
        
        # 测试查询扩展
        print("4. 测试查询扩展...")
        try:
            from embeddings import embedding_manager
            test_queries = [
                "生物医药",
                "初创企业", 
                "资金支持",
                "高新技术企业认定"
            ]
            
            for query in test_queries:
                expanded = embedding_manager.expand_query(query)
                print(f"   '{query}' -> {expanded[:3]}...")  # 只显示前3个
            print()
            
        except Exception as e:
            print(f"   ⚠ 查询扩展测试跳过 (需要模型): {e}")
            print()
        
        print("✅ 基础功能测试完成！")
        
    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        return False
    
    return True

def test_matching_logic():
    """测试匹配逻辑"""
    print("\n=== 智能匹配逻辑测试 ===\n")
    
    try:
        # 模拟政策内容
        mock_policies = [
            {
                "id": "policy_001",
                "title": "生物医药产业发展扶持政策",
                "content": "支持生物医药企业创新发展，对符合条件的企业给予最高100万元资金补贴。适用于生物制药、医疗器械、创新药物研发等领域的企业。初创企业优先支持。",
                "industries": ["生物医药"],
                "scales": ["初创企业", "小型企业", "中型企业"],
                "policy_type": "资金支持"
            },
            {
                "id": "policy_002", 
                "title": "高新技术企业认定管理办法",
                "content": "对认定为高新技术企业的，减按15%的税率征收企业所得税。申请条件包括企业注册满一年，研发费用占比不低于4%。",
                "industries": ["信息技术", "生物医药", "新材料"],
                "scales": ["中型企业", "大型企业"],
                "policy_type": "资质认定"
            },
            {
                "id": "policy_003",
                "title": "初创企业扶持专项基金",
                "content": "针对初创期企业设立专项扶持基金，给予最高50万元资金支持。重点支持科技创新、模式创新的初创企业。成立三年内的企业均可申请。",
                "industries": ["信息技术", "新能源", "生物医药"],
                "scales": ["初创企业"],
                "policy_type": "资金支持"
            },
            {
                "id": "policy_004",
                "title": "人才引进住房补贴政策",
                "content": "对引进的高层次人才提供住房补贴，博士学历人才最高补贴30万元，硕士学历人才最高补贴20万元。企业可为员工申请。",
                "industries": ["通用"],
                "scales": ["中小企业", "大型企业"],
                "policy_type": "人才政策"
            }
        ]
        
        # 测试不同类型的查询
        test_cases = [
            {
                "type": "自然语言查询",
                "query": "我想查找和生物医药相关的政策",
                "description": "测试行业关键词匹配"
            },
            {
                "type": "自然语言查询",
                "query": "我是一家小型初创企业，现阶段有什么政策比较适用",
                "description": "测试企业规模智能过滤"
            },
            {
                "type": "基础匹配",
                "params": {
                    "industry": "生物医药（含医疗器械）",
                    "company_scale": "初创企业（成立<3年，员工<20人）",
                    "demand_type": "资金补贴（如研发费用补助）"
                },
                "description": "测试结构化三选项匹配"
            },
            {
                "type": "基础匹配",
                "params": {
                    "industry": "新一代信息技术", 
                    "company_scale": "中小企业（员工20-200人）",
                    "demand_type": "资质认定（如高新企业、专精特新）"
                },
                "description": "测试资质认定类政策匹配"
            }
        ]
        
        from config import config
        
        for i, case in enumerate(test_cases, 1):
            print(f"{i}. {case['type']}: {case['description']}")
            
            if case['type'] == "自然语言查询":
                query = case['query']
                print(f"   查询: {query}")
                
                # 自然语言匹配逻辑
                matched_policies = []
                query_lower = query.lower()
                
                for policy in mock_policies:
                    score = 0
                    reasons = []
                    
                    # 内容语义匹配
                    content_lower = policy['content'].lower()
                    title_lower = policy['title'].lower()
                    
                    # 关键词匹配
                    query_words = query_lower.split()
                    content_words = content_lower.split()
                    common_words = set(query_words) & set(content_words)
                    if common_words:
                        score += len(common_words) * 0.1
                        reasons.append(f"关键词匹配: {list(common_words)}")
                    
                    # 行业智能匹配
                    for industry, keywords in config.INDUSTRY_MAPPING.items():
                        if any(keyword in query_lower for keyword in keywords):
                            if industry.replace("（含医疗器械）", "") in str(policy['industries']):
                                score += 0.4
                                reasons.append(f"行业匹配: {industry}")
                    
                    # 企业规模智能识别
                    for scale, scale_info in {
                        "初创企业": ["初创", "小型", "新成立", "起步"],
                        "中小企业": ["中小", "小型", "中型"], 
                        "大型企业": ["大型", "规模企业"]
                    }.items():
                        if any(keyword in query_lower for keyword in scale_info):
                            if scale in str(policy['scales']):
                                score += 0.3
                                reasons.append(f"规模匹配: {scale}")
                    
                    # 特殊逻辑：初创企业友好过滤
                    if "初创" in query_lower or "小型" in query_lower:
                        if "初创企业" in policy['scales']:
                            score += 0.2
                            reasons.append("初创企业友好")
                        elif policy['id'] == 'policy_002':  # 高新认定需要1年
                            score -= 0.3
                            reasons.append("可能不适合刚成立的企业")
                    
                    if score > 0.2:
                        matched_policies.append((policy, score, reasons))
                
            else:  # 基础匹配
                params = case['params']
                print(f"   参数: {params}")
                
                # 结构化匹配逻辑
                matched_policies = []
                
                # 提取匹配规则
                industry_keywords = []
                for industry, keywords in config.INDUSTRY_MAPPING.items():
                    if industry == params['industry']:
                        industry_keywords = keywords
                        break
                
                scale_keywords = []
                for scale, scale_info in {
                    "初创企业（成立<3年，员工<20人）": ["初创", "创业"],
                    "中小企业（员工20-200人）": ["中小", "小型", "中型"],
                    "大型企业（员工>200人）": ["大型", "规模企业"]
                }.items():
                    if scale == params['company_scale']:
                        scale_keywords = scale_info
                        break
                
                demand_keywords = []
                for demand, keywords in {
                    "资金补贴（如研发费用补助）": ["资金", "补贴", "补助", "奖励"],
                    "资质认定（如高新企业、专精特新）": ["认定", "资质", "高新", "专精特新"],
                    "人才支持（如落户、住房补贴）": ["人才", "落户", "住房", "补贴"],
                    "空间/设备（如实验室租金减免）": ["空间", "设备", "租金", "减免"]
                }.items():
                    if demand == params['demand_type']:
                        demand_keywords = keywords
                        break
                
                for policy in mock_policies:
                    score = 0
                    reasons = []
                    
                    # 行业匹配
                    content_lower = policy['content'].lower()
                    industry_matches = sum(1 for keyword in industry_keywords if keyword in content_lower)
                    if industry_matches > 0:
                        score += industry_matches * 0.15
                        reasons.append(f"行业匹配: {industry_matches}个关键词")
                    
                    # 需求类型匹配
                    demand_matches = sum(1 for keyword in demand_keywords if keyword in content_lower)
                    if demand_matches > 0:
                        score += demand_matches * 0.2
                        reasons.append(f"需求匹配: {demand_matches}个关键词")
                    
                    # 企业规模匹配
                    if params['company_scale'].startswith("初创企业"):
                        if "初创企业" in policy['scales']:
                            score += 0.25
                            reasons.append("适合初创企业")
                        elif policy['id'] == 'policy_002':
                            score -= 0.2
                            reasons.append("需要企业成立满一年")
                    
                    if score > 0.2:
                        matched_policies.append((policy, score, reasons))
            
            # 按分数排序并展示结果
            matched_policies.sort(key=lambda x: x[1], reverse=True)
            
            print(f"   匹配到 {len(matched_policies)} 个政策:")
            for j, (policy, score, reasons) in enumerate(matched_policies[:3], 1):
                match_level = "高" if score >= 0.8 else "中" if score >= 0.5 else "低"
                print(f"     {j}. {policy['title']}")
                print(f"        匹配度: {match_level} ({score:.3f})")
                print(f"        政策类型: {policy['policy_type']}")
                print(f"        匹配原因: {', '.join(reasons[:2])}")
                
                # 生成建议
                suggestions = []
                if policy['policy_type'] == "资金支持":
                    suggestions.append("建议准备详细的资金使用计划")
                if policy['policy_type'] == "资质认定":
                    suggestions.append("建议先了解认定条件和流程")
                if "初创" in str(policy['scales']) and case.get('query', '').find('初创') >= 0:
                    suggestions.append("作为初创企业，此政策门槛较低")
                
                if suggestions:
                    print(f"        申请建议: {suggestions[0]}")
                print()
        
        print("✅ 智能匹配逻辑测试完成！")
        
    except Exception as e:
        print(f"❌ 智能匹配逻辑测试失败: {e}")
        return False
    
    return True

def show_api_usage_examples():
    """显示API使用示例"""
    print("\n=== 统一API使用示例 ===\n")
    
    examples = {
        "服务信息": {
            "服务地址": "http://localhost:8000",
            "API文档": "http://localhost:8000/docs",
            "OpenAPI规范": "http://localhost:8000/openapi.json"
        },
        "自然语言查询": {
            "标准搜索": {
                "endpoint": "POST /search",
                "request": {
                    "query": "我想查找和生物医药相关的政策",
                    "industry": "生物医药（含医疗器械）",
                    "enterprise_scale": "初创企业（成立<3年，员工<20人）",
                    "top_k": 5
                },
                "description": "支持复杂自然语言查询，智能理解用户意图"
            },
            "快速搜索": {
                "endpoint": "GET /search/quick",
                "url": "/search/quick?q=初创企业政策&industry=生物医药&top_k=3",
                "description": "简化的GET方式查询接口"
            }
        },
        "一键匹配": {
            "基础匹配": {
                "endpoint": "POST /basic-match",
                "request": {
                    "industry": "生物医药（含医疗器械）",
                    "company_scale": "初创企业（成立<3年，员工<20人）",
                    "demand_type": "资金补贴（如研发费用补助）"
                },
                "description": "三选项快速匹配，适合初步筛选"
            },
            "精准匹配": {
                "endpoint": "POST /precise-match", 
                "request": {
                    "basic_request": {
                        "industry": "新一代信息技术",
                        "company_scale": "初创企业（成立<3年，员工<20人）",
                        "demand_type": "资质认定（如高新企业、专精特新）"
                    },
                    "company_info": {
                        "company_name": "北京智能科技有限公司",
                        "company_type": "有限责任公司",
                        "registered_capital": "500万元",
                        "establishment_date": "2023-01-15",
                        "registered_address": "北京市海淀区中关村",
                        "business_scope": "人工智能技术研发；软件开发",
                        "honors_qualifications": ["中关村高新技术企业"]
                    }
                },
                "description": "基于企业详细信息的深度分析匹配"
            }
        },
        "系统管理": {
            "配置查询": "GET /config",
            "健康检查": "GET /health", 
            "系统状态": "GET /status",
            "企业信息": "GET /company-info/{company_name}",
            "查询示例": "GET /examples",
            "政策分类": "GET /categories"
        }
    }
    
    print(json.dumps(examples, indent=2, ensure_ascii=False))

def show_system_features():
    """展示系统特性"""
    print("\n=== 系统核心特性 ===\n")
    
    features = {
        "统一架构": [
            "🚀 单一API服务：所有功能通过统一接口提供",
            "⚡ FastAPI框架：高性能、自动文档生成", 
            "🔧 模块化设计：组件独立可扩展",
            "📖 智能集成：自然语言+结构化匹配融合"
        ],
        "智能化程度": [
            "🧠 自然语言理解：支持复杂中文查询表达",
            "🎯 意图识别：智能理解用户真实需求",
            "🔍 实体提取：自动识别行业、规模、类型等关键信息",
            "📈 查询扩展：基于语义相似性生成相关查询"
        ],
        "匹配精度": [
            "🎪 多维度算法：行业+规模+需求综合评分",
            "🏢 企业画像分析：基于详细信息的深度理解",
            "⚡ 动态评分：实时调整匹配分数",
            "🎚️ 智能过滤：初创企业友好策略"
        ],
        "用户体验": [
            "📊 清晰展示：高/中/低匹配度等级显示",
            "💡 个性化建议：针对性申请建议和策略",
            "⚡ 快速响应：秒级查询处理",
            "📖 完善文档：自动生成的交互式API文档"
        ]
    }
    
    for category, items in features.items():
        print(f"### {category}")
        for item in items:
            print(f"  {item}")
        print()

def main():
    """主测试函数"""
    print("政策匹配RAG检索系统 - 统一API演示")
    print("=" * 60)
    
    # 基础功能测试
    basic_success = test_without_dependencies()
    
    # 匹配逻辑测试
    if basic_success:
        test_matching_logic()
    
    # 显示API使用示例
    show_api_usage_examples()
    
    # 展示系统特性
    show_system_features()
    
    print("\n" + "=" * 60)
    print("🛠️  启动方式:")
    print("   1. 一键启动: python start_production.py")
    print("   2. 主程序启动: python main.py") 
    print("   3. 直接启动API: python api.py")
    print("\n🧪 测试方式:")
    print("   1. 完整API测试: python test_api.py")
    print("   2. 当前演示测试: python test_demo.py")
    print("\n📖 文档访问:")
    print("   1. 交互式API文档: http://localhost:8000/docs")
    print("   2. 生产使用说明: PRODUCTION_README.md")
    print("\n🎯 核心功能:")
    print("   ✅ 自然语言查询 - 智能理解复杂中文表达")
    print("   ✅ 一键匹配功能 - 三选项快速匹配")
    print("   ✅ 精准匹配分析 - 基于企业详细信息")
    print("   ✅ 智能过滤策略 - 初创企业友好机制")
    print("   ✅ 统一API架构 - 所有功能一个接口解决")
    print("\n🚀 立即体验: 访问 http://localhost:8000/docs")

if __name__ == "__main__":
    main() 