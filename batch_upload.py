#!/usr/bin/env python3
"""
批量上传政策文档脚本
使用方法：python batch_upload.py [文档目录]
"""

import sys
import os
from pathlib import Path
from policy_matcher import get_policy_matcher

def batch_upload_policies(directory: str) -> None:
    """
    批量上传目录中的所有政策文档
    
    Args:
        directory: 文档目录路径
    """
    
    if not os.path.exists(directory):
        print(f"❌ 目录不存在: {directory}")
        return
    
    # 支持的文件格式
    allowed_extensions = {'.pdf', '.docx', '.txt'}
    
    # 找到所有符合条件的文件
    files_to_upload = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in allowed_extensions:
                files_to_upload.append(os.path.join(root, file))
    
    if not files_to_upload:
        print(f"📁 在目录 {directory} 中未找到支持的文档文件")
        print(f"支持的格式: {', '.join(allowed_extensions)}")
        return
    
    print(f"📚 找到 {len(files_to_upload)} 个文档文件:")
    for i, file_path in enumerate(files_to_upload, 1):
        filename = Path(file_path).name
        size_kb = os.path.getsize(file_path) / 1024
        print(f"  {i}. {filename} ({size_kb:.2f} KB)")
    
    # 确认是否继续
    print(f"\n🤔 确认要上传这 {len(files_to_upload)} 个文件吗？(y/N): ", end="")
    confirm = input().strip().lower()
    
    if confirm not in ['y', 'yes']:
        print("⏹ 操作已取消")
        return
    
    # 开始批量上传
    print("\n" + "=" * 50)
    print("🚀 开始批量上传...")
    print("=" * 50)
    
    matcher = get_policy_matcher()
    
    # 检查初始数据状态
    initial_status = matcher.get_system_status()
    initial_count = initial_status.get('vector_store', {}).get('milvus_stats', {}).get('row_count', 0)
    print(f"📊 初始数据量: {initial_count}")
    
    success_count = 0
    failed_files = []
    
    for i, file_path in enumerate(files_to_upload, 1):
        filename = Path(file_path).name
        print(f"\n📄 [{i}/{len(files_to_upload)}] 处理: {filename}")
        
        try:
            success = matcher.add_policy_document(file_path)
            if success:
                print(f"✅ {filename} 处理成功")
                success_count += 1
            else:
                print(f"❌ {filename} 处理失败")
                failed_files.append(filename)
        except Exception as e:
            print(f"❌ {filename} 处理出错: {e}")
            failed_files.append(filename)
    
    # 最终结果统计
    print("\n" + "=" * 50)
    print("📊 批量上传完成！")
    print("=" * 50)
    
    print(f"✅ 成功处理: {success_count} 个文件")
    print(f"❌ 失败文件: {len(failed_files)} 个")
    
    if failed_files:
        print("\n💥 失败的文件:")
        for filename in failed_files:
            print(f"  - {filename}")
    
    # 检查最终数据状态
    final_status = matcher.get_system_status()
    final_count = final_status.get('vector_store', {}).get('milvus_stats', {}).get('row_count', 0)
    print(f"\n📊 最终数据量: {final_count}")
    print(f"📈 新增数据: {final_count - initial_count} 条记录")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python batch_upload.py [文档目录]")
        print("\n示例:")
        print("  python batch_upload.py ./policies/")
        print("  python batch_upload.py /path/to/policy/documents/")
        
        print("\n支持的格式: PDF, DOCX, TXT")
        print("会递归搜索子目录中的文档文件")
        return
    
    directory = sys.argv[1]
    
    print("=" * 50)
    print("📚 政策文档批量上传工具")
    print("=" * 50)
    
    batch_upload_policies(directory)

if __name__ == "__main__":
    main()
