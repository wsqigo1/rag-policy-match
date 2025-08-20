#!/usr/bin/env python3
"""
新政策文档上传脚本
使用方法：python upload_new_policy.py [文档路径]
"""

import sys
import os
from pathlib import Path
from policy_matcher import get_policy_matcher

def upload_policy_document(file_path: str) -> bool:
    """
    上传并处理政策文档
    
    Args:
        file_path: 文档文件路径
        
    Returns:
        bool: 处理是否成功
    """
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    # 检查文件格式
    allowed_extensions = {'.pdf', '.docx', '.txt'}
    file_extension = Path(file_path).suffix.lower()
    
    if file_extension not in allowed_extensions:
        print(f"❌ 不支持的文件格式: {file_extension}")
        print(f"支持的格式: {', '.join(allowed_extensions)}")
        return False
    
    print(f"📄 准备处理文档: {file_path}")
    print(f"📁 文件大小: {os.path.getsize(file_path) / 1024:.2f} KB")
    
    try:
        # 获取政策匹配器实例
        matcher = get_policy_matcher()
        
        # 检查上传前的数据状态
        status = matcher.get_system_status()
        milvus_stats = status.get('vector_store', {}).get('milvus_stats', {})
        before_count = milvus_stats.get('row_count', 0)
        
        print(f"📊 上传前数据量: {before_count}")
        print("🔄 正在处理文档...")
        
        # 处理文档
        success = matcher.add_policy_document(file_path)
        
        if success:
            print("✅ 文档处理成功！")
            
            # 检查处理后的数据状态
            new_status = matcher.get_system_status()
            new_milvus_stats = new_status.get('vector_store', {}).get('milvus_stats', {})
            after_count = new_milvus_stats.get('row_count', 0)
            
            print(f"📊 处理后数据量: {after_count}")
            print(f"📈 新增数据: {after_count - before_count} 条记录")
            
            print("\n🔍 验证文档是否可以被检索...")
            
            # 简单验证检索
            from models import BasicMatchRequest
            test_request = BasicMatchRequest(
                industry='新一代信息技术',
                company_scale='中小企业（员工20-200人）',
                demand_type='资金补贴（如研发费用补助）'
            )
            
            response = matcher.basic_match(test_request)
            
            # 检查是否能找到新文档
            filename = Path(file_path).stem
            for match in response.matches[:5]:
                if filename.lower() in match.policy_name.lower():
                    print(f"🎉 新文档已被成功索引！")
                    print(f"   政策名称: {match.policy_name}")
                    print(f"   匹配分数: {match.match_score}")
                    break
            else:
                print("⚠️ 在检索结果中暂未找到新文档（索引可能需要一些时间）")
            
            return True
        else:
            print("❌ 文档处理失败")
            return False
            
    except Exception as e:
        print(f"❌ 处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python upload_new_policy.py [文档路径]")
        print("\n示例:")
        print("  python upload_new_policy.py 新政策文档.pdf")
        print("  python upload_new_policy.py /path/to/policy.docx")
        print("  python upload_new_policy.py policy.txt")
        
        print("\n支持的格式: PDF, DOCX, TXT")
        return
    
    file_path = sys.argv[1]
    
    print("=" * 50)
    print("🚀 政策文档上传处理工具")
    print("=" * 50)
    
    success = upload_policy_document(file_path)
    
    if success:
        print("\n🎉 上传处理完成！新政策数据已添加到系统中。")
    else:
        print("\n💥 上传处理失败！请检查错误信息。")

if __name__ == "__main__":
    main()

