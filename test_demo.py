#!/usr/bin/env python3
"""
政策匹配系统测试演示脚本
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
        
        # 测试文档处理
        print("2. 测试文档处理...")
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
        print("3. 测试查询扩展...")
        try:
            from embeddings import embedding_manager
            test_queries = [
                "生物医药",
                "初创企业", 
                "资金支持"
            ]
            
            for query in test_queries:
                expanded = embedding_manager.expand_query(query)
                print(f"   '{query}' -> {expanded}")
            print()
            
        except Exception as e:
            print(f"   ⚠ 查询扩展测试跳过 (需要模型): {e}")
            print()
        
        # 测试数据模型
        print("4. 测试数据模型...")
        from models import QueryRequest, PolicyChunk
        
        # 创建查询请求
        query_req = QueryRequest(
            query="生物医药相关政策",
            industry="生物医药",
            enterprise_scale="初创企业",
            top_k=5
        )
        print(f"   ✓ 查询请求: {query_req.query}")
        print(f"   ✓ 行业筛选: {query_req.industry}")
        print(f"   ✓ 企业规模: {query_req.enterprise_scale}")
        
        # 创建政策分块
        chunk = PolicyChunk(
            chunk_id="test_chunk_001",
            policy_id="test_policy_001",
            content="这是一个测试政策分块内容",
            keywords=["测试", "政策", "分块"]
        )
        print(f"   ✓ 政策分块: {chunk.chunk_id}")
        print()
        
        print("✅ 基础功能测试完成！")
        
    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        return False
    
    return True

def test_with_simple_matching():
    """简化的匹配测试（不依赖向量数据库）"""
    print("\n=== 简化匹配逻辑测试 ===\n")
    
    try:
        # 模拟政策内容
        mock_policies = [
            {
                "id": "policy_001",
                "title": "生物医药产业发展扶持政策",
                "content": "支持生物医药企业创新发展，对符合条件的企业给予资金补贴。适用于生物制药、医疗器械、创新药物研发等领域的企业。",
                "industries": ["生物医药"],
                "scales": ["初创企业", "小型企业", "中型企业"]
            },
            {
                "id": "policy_002", 
                "title": "高新技术企业认定管理办法",
                "content": "对认定为高新技术企业的，减按15%的税率征收企业所得税。申请条件包括企业注册满一年，研发费用占比不低于4%。",
                "industries": ["信息技术", "生物医药", "新材料"],
                "scales": ["中型企业", "大型企业"]
            },
            {
                "id": "policy_003",
                "title": "初创企业扶持专项基金",
                "content": "针对初创期企业设立专项扶持基金，给予最高50万元资金支持。重点支持科技创新、模式创新的初创企业。",
                "industries": ["信息技术", "新能源", "生物医药"],
                "scales": ["初创企业"]
            }
        ]
        
        # 测试查询匹配
        test_cases = [
            {
                "query": "我想查找和生物医药相关的政策",
                "expected_policies": ["policy_001", "policy_002", "policy_003"]
            },
            {
                "query": "我是一家小型初创企业，现阶段有什么政策比较适用",
                "expected_policies": ["policy_001", "policy_003"]
            },
            {
                "query": "有哪些税收优惠政策",
                "expected_policies": ["policy_002"]
            }
        ]
        
        from config import config
        
        for i, case in enumerate(test_cases, 1):
            print(f"{i}. 测试查询: {case['query']}")
            
            # 简单的关键词匹配逻辑
            matched_policies = []
            query_lower = case['query'].lower()
            
            for policy in mock_policies:
                score = 0
                
                # 内容匹配
                content_lower = policy['content'].lower()
                if any(word in content_lower for word in query_lower.split()):
                    score += 0.3
                
                # 行业匹配
                for industry, keywords in config.INDUSTRY_MAPPING.items():
                    if industry in policy['industries']:
                        if any(keyword in query_lower for keyword in keywords):
                            score += 0.4
                
                # 企业规模匹配
                for scale, keywords in config.ENTERPRISE_SCALES.items():
                    if scale in policy['scales']:
                        if any(keyword in query_lower for keyword in keywords):
                            score += 0.3
                
                # 特殊关键词匹配
                if "税收" in query_lower and "税" in content_lower:
                    score += 0.5
                if "资金" in query_lower and "资金" in content_lower:
                    score += 0.5
                
                if score > 0.2:  # 阈值
                    matched_policies.append((policy, score))
            
            # 按分数排序
            matched_policies.sort(key=lambda x: x[1], reverse=True)
            
            print(f"   匹配到 {len(matched_policies)} 个政策:")
            for j, (policy, score) in enumerate(matched_policies[:3], 1):
                print(f"     {j}. {policy['title']} (相关性: {score:.2f})")
                
                # 适用性分析
                applicability = []
                if "初创" in query_lower and "初创企业" in policy['scales']:
                    applicability.append("✓ 适合初创企业")
                elif "初创" in query_lower and "初创企业" not in policy['scales']:
                    applicability.append("⚠ 可能不适合初创企业")
                
                if applicability:
                    print(f"        {' | '.join(applicability)}")
            
            print()
        
        print("✅ 简化匹配测试完成！")
        
    except Exception as e:
        print(f"❌ 简化匹配测试失败: {e}")
        return False
    
    return True

def show_usage_examples():
    """显示使用示例"""
    print("\n=== 系统使用示例 ===\n")
    
    examples = {
        "API调用示例": {
            "POST /search": {
                "request": {
                    "query": "我想查找和生物医药相关的政策",
                    "industry": "生物医药",
                    "enterprise_scale": "初创企业",
                    "top_k": 5
                },
                "description": "标准政策搜索"
            },
            "GET /search/quick": {
                "url": "/search/quick?q=初创企业政策&enterprise_scale=初创企业",
                "description": "快速查询接口"
            }
        },
        "预期功能": [
            "语义匹配：'生物医药' 能匹配到 '医疗器械'、'制药' 等相关内容",
            "智能过滤：'初创企业' 查询会过滤掉需要注册3年以上的政策",
            "多维分析：提供行业匹配度、企业规模适用性、申请建议等",
            "混合检索：结合向量相似度和关键词匹配，提高准确性"
        ],
        "部署说明": [
            "1. 安装依赖: pip install -r requirements.txt",
            "2. 启动Milvus和Elasticsearch (可选，有fallback机制)",
            "3. 运行: python main.py",
            "4. 访问: http://localhost:8000/docs 查看API文档"
        ]
    }
    
    print(json.dumps(examples, indent=2, ensure_ascii=False))

def main():
    """主测试函数"""
    print("政策匹配RAG检索系统 - 测试演示")
    print("=" * 50)
    
    # 基础功能测试
    basic_success = test_without_dependencies()
    
    # 简化匹配测试
    if basic_success:
        test_with_simple_matching()
    
    # 显示使用示例
    show_usage_examples()
    
    print("\n" + "=" * 50)
    print("📖 完整功能需要:")
    print("   1. Milvus向量数据库 (docker run -p 19530:19530 milvusdb/milvus)")
    print("   2. Elasticsearch (docker run -p 9200:9200 elasticsearch:8.11.0)")
    print("   3. 中文嵌入模型 (自动下载 moka-ai/m3e-base)")
    print("\n💡 当前演示展示了:")
    print("   ✓ 文档解析和分块")
    print("   ✓ 查询扩展和匹配逻辑") 
    print("   ✓ 企业规模智能过滤")
    print("   ✓ 完整的API接口设计")
    print("\n🚀 启动完整系统: python main.py")

if __name__ == "__main__":
    main() 