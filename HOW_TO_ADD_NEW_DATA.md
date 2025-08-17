# 🚀 如何添加新的政策数据

本指南详细介绍如何向政策匹配系统中添加新的政策数据。

## 📋 支持的文件格式

- ✅ **PDF** (.pdf) - 推荐，支持复杂格式
- ✅ **DOCX** (.docx) - Word文档
- ✅ **TXT** (.txt) - 纯文本文档

## 🎯 添加方法

### 方法1：单文件上传（推荐）

```bash
# 上传单个政策文档
python upload_new_policy.py "新政策.pdf"
```

**优势：**
- ✅ 简单易用，一条命令完成
- ✅ 自动验证文件格式
- ✅ 实时显示处理进度
- ✅ 自动验证索引效果

### 方法2：批量上传

```bash
# 批量上传目录中的所有文档
python batch_upload.py "./policy_documents/"
```

**优势：**
- ✅ 支持目录递归搜索
- ✅ 批量处理多个文件
- ✅ 详细的统计报告
- ✅ 失败文件记录

### 方法3：API接口上传

#### 启动API服务
```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

#### 使用curl上传
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@政策文档.pdf"
```

#### 使用Python requests
```python
import requests

url = "http://localhost:8000/upload"
files = {"file": open("政策文档.pdf", "rb")}

response = requests.post(url, files=files)
print(response.json())
```

**优势：**
- ✅ 标准REST API
- ✅ 支持Web前端集成
- ✅ 异步后台处理
- ✅ 适合自动化系统

## 🔧 处理流程

系统接收文档后会自动进行以下处理：

1. **📄 文档解析** - 提取文本内容和结构化信息
2. **🔍 智能分块** - 将文档分割成语义相关的块
3. **🧠 向量化** - 将文本转换为768维向量
4. **💾 存储** - 保存到Milvus向量数据库
5. **🏷️ 索引** - 创建可搜索的索引
6. **✅ 验证** - 确保数据可被正常检索

## 📊 验证方法

### 检查系统状态
```bash
python -c "
from policy_matcher import get_policy_matcher
matcher = get_policy_matcher()
status = matcher.get_system_status()
print('数据量:', status['vector_store']['milvus_stats']['row_count'])
"
```

### 测试检索效果
```bash
python -c "
from models import BasicMatchRequest
from policy_matcher import get_policy_matcher

matcher = get_policy_matcher()
request = BasicMatchRequest(
    industry='新一代信息技术',
    company_scale='中小企业（员工20-200人）',
    demand_type='资金补贴（如研发费用补助）'
)

response = matcher.basic_match(request)
for match in response.matches[:3]:
    print(f'- {match.policy_name} (匹配度: {match.match_score})')
"
```

## ⚠️ 注意事项

### 文件要求
- 📝 文档内容应为中文政策文本
- 📏 文件大小建议不超过50MB
- 🔤 文件名建议使用中文，描述政策内容

### 最佳实践
- 🎯 **文档质量**：内容完整、格式规范的文档效果更好
- 📚 **批量上传**：大量文档建议使用批量上传脚本
- 🔍 **定期验证**：上传后建议测试检索效果
- 💾 **备份重要**：重要文档建议保留原始备份

### 常见问题

**Q: 上传后看不到效果？**
A: 索引需要一些时间，建议等待几分钟后再测试

**Q: 文件格式不支持？**
A: 目前支持PDF、DOCX、TXT格式，其他格式请转换后上传

**Q: 处理失败怎么办？**
A: 检查文件是否损坏，内容是否为中文，格式是否正确

## 🎉 成功示例

```bash
$ python upload_new_policy.py "北京市科技创新支持政策.pdf"

==================================================
🚀 政策文档上传处理工具
==================================================
📄 准备处理文档: 北京市科技创新支持政策.pdf
📁 文件大小: 1.25 MB
📊 上传前数据量: 1000
🔄 正在处理文档...
✅ 文档处理成功！
📊 处理后数据量: 1065
📈 新增数据: 65 条记录

🔍 验证文档是否可以被检索...
🎉 新文档已被成功索引！
   政策名称: 北京市科技创新支持政策
   匹配分数: 1.0

🎉 上传处理完成！新政策数据已添加到系统中。
```

## 🔗 相关链接

- [系统API文档](./PRODUCTION_README.md)
- [项目说明](./README.md)
- [配置说明](./config.py)

---

💡 **提示：** 有任何问题可以查看日志文件 `policy_matcher.log` 获取详细信息。
