#!/usr/bin/env python3
"""
政策匹配统一API测试脚本
测试集成后的自然语言查询和一键匹配功能
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """测试健康检查接口"""
    print("\n=== 测试健康检查接口 ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"健康检查失败: {e}")
        return False

def test_get_config():
    """测试获取配置接口"""
    print("\n=== 测试获取配置接口 ===")
    try:
        response = requests.get(f"{BASE_URL}/config")
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"行业选项数量: {len(data['industries'])}")
        print(f"企业规模选项: {data['company_scales']}")
        print(f"需求类型选项: {data['demand_types']}")
        return response.status_code == 200
    except Exception as e:
        print(f"配置获取失败: {e}")
        return False

def test_natural_language_search():
    """测试自然语言搜索接口"""
    print("\n=== 测试自然语言搜索接口 ===")
    try:
        # 测试数据
        test_data = {
            "query": "我想查找和生物医药相关的政策",
            "top_k": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/search",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"状态码: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            print(f"查询结果数量: {data['total_results']}")
            print(f"处理时间: {data['processing_time']:.3f}秒")
            
            if data['results']:
                first_result = data['results'][0]
                print(f"\n第一个匹配结果:")
                print(f"  政策标题: {first_result['title']}")
                print(f"  相关性分数: {first_result['relevance_score']:.3f}")
                print(f"  摘要: {first_result['summary'][:100]}...")
                
            if data['suggestions']:
                print(f"\n搜索建议: {data['suggestions']}")
        else:
            print(f"搜索失败: {data}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"自然语言搜索测试失败: {e}")
        return False

def test_quick_search():
    """测试快速搜索接口"""
    print("\n=== 测试快速搜索接口 ===")
    try:
        params = {
            "q": "初创企业政策",
            "industry": "新一代信息技术",
            "enterprise_scale": "初创企业（成立<3年，员工<20人）",
            "top_k": 3
        }
        
        response = requests.get(f"{BASE_URL}/search/quick", params=params)
        
        print(f"状态码: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            print(f"查询结果数量: {data['total_results']}")
            print(f"处理时间: {data['processing_time']:.3f}秒")
        else:
            print(f"快速搜索失败: {data}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"快速搜索测试失败: {e}")
        return False

def test_basic_match():
    """测试基础匹配接口"""
    print("\n=== 测试基础匹配接口 ===")
    try:
        # 测试数据
        test_data = {
            "industry": "生物医药（含医疗器械）",
            "company_scale": "初创企业（成立<3年，员工<20人）",
            "demand_type": "资金补贴（如研发费用补助）"
        }
        
        response = requests.post(
            f"{BASE_URL}/basic-match",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"状态码: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            print(f"匹配结果数量: {data['total_results']}")
            print(f"处理时间: {data['processing_time']:.3f}秒")
            print(f"匹配类型: {data['match_type']}")
            
            if data['matches']:
                first_match = data['matches'][0]
                print(f"\n第一个匹配政策:")
                print(f"  政策名称: {first_match['policy_name']}")
                print(f"  匹配度: {first_match['match_level']}")
                print(f"  匹配分数: {first_match['match_score']:.3f}")
                print(f"  政策类型: {first_match['policy_type']}")
                print(f"  关键描述: {first_match['key_description'][:100]}...")
                
            if data['suggestions']:
                print(f"\n匹配建议: {data['suggestions']}")
        else:
            print(f"基础匹配失败: {data}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"基础匹配测试失败: {e}")
        return False

def test_precise_match():
    """测试精准匹配接口"""
    print("\n=== 测试精准匹配接口 ===")
    try:
        # 测试数据
        test_data = {
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
                "business_scope": "人工智能技术研发；软件开发；技术咨询服务",
                "honors_qualifications": ["中关村高新技术企业"]
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/precise-match",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"状态码: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            print(f"精准匹配结果数量: {data['total_results']}")
            print(f"处理时间: {data['processing_time']:.3f}秒")
            print(f"匹配类型: {data['match_type']}")
            
            if data['matches']:
                first_match = data['matches'][0]
                print(f"\n第一个匹配政策:")
                print(f"  政策名称: {first_match['policy_name']}")
                print(f"  匹配度: {first_match['match_level']}")
                print(f"  匹配分数: {first_match['match_score']:.3f}")
                print(f"  政策类型: {first_match['policy_type']}")
                
            if data['suggestions']:
                print(f"\n精准建议: {data['suggestions']}")
        else:
            print(f"精准匹配失败: {data}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"精准匹配测试失败: {e}")
        return False

def test_company_info():
    """测试企业信息查询接口"""
    print("\n=== 测试企业信息查询接口 ===")
    try:
        company_name = "北京科技有限公司"
        response = requests.get(f"{BASE_URL}/company-info/{company_name}")
        
        print(f"状态码: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            print(f"企业名称: {data['company_name']}")
            print(f"企业类型: {data['company_type']}")
            print(f"注册资本: {data['registered_capital']}")
            print(f"成立时间: {data['establishment_date']}")
            print(f"已有资质: {data.get('honors_qualifications', [])}")
        else:
            print(f"查询失败: {data}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"企业信息查询测试失败: {e}")
        return False

def test_system_status():
    """测试系统状态接口"""
    print("\n=== 测试系统状态接口 ===")
    try:
        response = requests.get(f"{BASE_URL}/status")
        
        print(f"状态码: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            print(f"系统状态: {data['status']}")
            print(f"政策总数: {data['total_policies']}")
            print(f"向量库状态: {data['vector_store_status']}")
        else:
            print(f"状态查询失败: {data}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"系统状态测试失败: {e}")
        return False

def test_examples():
    """测试示例接口"""
    print("\n=== 测试示例接口 ===")
    try:
        response = requests.get(f"{BASE_URL}/examples")
        
        print(f"状态码: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            examples = data['examples']
            print(f"自然语言查询示例数量: {len(examples['natural_language'])}")
            print(f"基础匹配示例: {examples['basic_match']['industry']}")
            print(f"精准匹配示例企业: {examples['precise_match']['company_info']['company_name']}")
        else:
            print(f"示例获取失败: {data}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"示例接口测试失败: {e}")
        return False

def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    try:
        # 测试缺少参数的情况
        response = requests.post(
            f"{BASE_URL}/basic-match",
            json={"industry": "生物医药"},  # 缺少其他必需参数
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"错误测试状态码: {response.status_code}")
        print(f"错误响应: {response.json()}")
        
        return response.status_code == 422  # FastAPI返回422错误
        
    except Exception as e:
        print(f"错误处理测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始统一API测试...")
    
    tests = [
        ("健康检查", test_health_check),
        ("配置获取", test_get_config),
        ("自然语言搜索", test_natural_language_search),
        ("快速搜索", test_quick_search),
        ("基础匹配", test_basic_match),
        ("精准匹配", test_precise_match),
        ("企业信息查询", test_company_info),
        ("系统状态", test_system_status),
        ("示例接口", test_examples),
        ("错误处理", test_error_handling)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"执行测试: {test_name}")
        
        start_time = time.time()
        result = test_func()
        end_time = time.time()
        
        if result:
            print(f"✅ {test_name} 测试通过 ({end_time - start_time:.2f}秒)")
            passed += 1
        else:
            print(f"❌ {test_name} 测试失败")
    
    print(f"\n{'='*50}")
    print(f"测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！统一API服务正常工作")
        print("\n📋 API功能验证:")
        print("  ✅ 自然语言查询功能正常")
        print("  ✅ 一键匹配功能正常")
        print("  ✅ 企业信息查询正常")
        print("  ✅ 系统状态监控正常")
        print("  ✅ 配置管理正常")
    else:
        print("⚠️  部分测试失败，请检查服务状态")

if __name__ == "__main__":
    print("请确保API服务已启动:")
    print("  方式1: python main.py")
    print("  方式2: python start_production.py")
    print("  方式3: python api.py")
    print("\nAPI地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("等待5秒后开始测试...")
    time.sleep(5)
    
    main() 