# 政策匹配系统 - 生产版本

## 系统概述

本系统提供**智能政策匹配服务**，通过**统一API接口**支持智能查询政策、自测通过率算法和一键匹配功能，为企业提供全方位的政策推荐和评估服务。

## 核心功能

### 1. 智能查询政策 🧠
- **自然语言理解**：支持复杂中文表达，如"我想查找和生物医药相关的政策"
- **意图识别**：自动识别查询意图（政策查找、适用性检查、资金支持、申请条件）
- **实体提取**：智能识别行业、企业规模、政策类型、金额要求等关键信息
- **智能过滤**：初创企业查询自动排除高门槛政策，避免不适用推荐
- **动态权重**：根据查询复杂度自动调整算法权重，优化匹配效果

### 2. 自测通过率算法 📊
- **智能评估**：企业输入基本信息，系统计算对特定政策的申请通过率
- **条件分析**：详细分析已满足条件、待完善条件和不确定条件
- **通过率等级**：高（≥70%）、中（40-69%）、低（<40%）三个等级
- **个性化建议**：基于分析结果提供具体的改进建议和申请策略
- **实时计算**：支持动态调整企业信息，实时更新通过率

### 3. 一键匹配功能 🎪
- **基础匹配**：三选项快速匹配（行业、规模、需求）
- **精准匹配**：基于企业详细信息的深度匹配
- 智能评分和匹配度分析
- 企业画像分析和个性化建议

### 4. 统一架构 🚀
- **单一API服务**：所有功能通过统一接口提供
- **FastAPI框架**：高性能、自动文档生成
- **智能集成**：自然语言处理与结构化匹配的完美融合

## 快速启动

### 方式1：一键启动（推荐）
```bash
python start_production.py
```

### 方式2：主程序启动
```bash
python main.py
```

### 方式3：直接启动API
```bash
python api.py
```

### 运行测试
```bash
# 测试智能查询功能
python demo_intelligent_query.py

# 测试自测通过率算法
python demo_eligibility.py
python test_eligibility.py

# 测试所有API功能
python test_api.py
```

## API接口文档

### 服务信息
- **服务地址**: http://localhost:8000
- **API文档**: http://localhost:8000/docs （自动生成的交互式文档）
- **OpenAPI规范**: http://localhost:8000/openapi.json

### 智能查询政策

#### 自然语言智能搜索
```http
POST http://localhost:8000/search
Content-Type: application/json

{
    "query": "我想查找和生物医药相关的政策",
    "industry": "生物医药（含医疗器械）",  // 可选
    "enterprise_scale": "初创企业（成立<3年，员工<20人）",  // 可选
    "policy_type": "资金支持",  // 可选
    "region": "北京",  // 可选
    "top_k": 10  // 可选，默认10
}
```

**智能处理能力**：
- 意图识别：find_policy、check_eligibility、get_funding、get_requirements
- 实体提取：行业、企业规模、政策类型、金额要求、时间要求
- 智能过滤：初创企业友好、排除高门槛政策
- 查询扩展：基于语义相似性扩展查询词
- 动态权重：根据查询复杂度调整算法权重

#### 快速搜索
```http
GET http://localhost:8000/search/quick?q=生物医药政策&industry=生物医药&top_k=5
```

### 自测通过率算法

#### 政策资格自测分析
```http
POST http://localhost:8000/analyze-eligibility
Content-Type: application/json

{
    "policy_id": "policy_157f44c2",
    "company_info": {
        "company_name": "北京测试科技有限公司",
        "establishment_date": "2023-01-15",
        "registered_capital": "500万元",
        "business_scope": "软件开发、人工智能技术研发",
        "employee_count": 15,
        "rd_personnel_ratio": 60,
        "rd_expense_ratio": 8,
        "high_tech_income_ratio": 45,
        "has_ip": true,
        "ip_count": 3,
        "annual_revenue": "200万元",
        "has_audit_report": false
    },
    "additional_info": {
        "recent_revenue": "200万元",
        "has_audit_report": false,
        "certification_status": "申请中"
    }
}
```

#### 获取自测模板
```http
GET http://localhost:8000/eligibility-template
```

#### 查询政策申请条件
```http
GET http://localhost:8000/policy-conditions/{policy_id}
```

### 一键匹配

#### 基础匹配
```http
POST http://localhost:8000/basic-match
Content-Type: application/json

{
    "industry": "生物医药（含医疗器械）",
    "company_scale": "初创企业（成立<3年，员工<20人）",
    "demand_type": "资金补贴（如研发费用补助）"
}
```

#### 精准匹配
```http
POST http://localhost:8000/precise-match
Content-Type: application/json

{
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
}
```

### 系统管理

#### 获取配置选项
```http
GET http://localhost:8000/config
```

#### 健康检查
```http
GET http://localhost:8000/health
```

#### 系统状态
```http
GET http://localhost:8000/status
```

#### 企业信息查询
```http
GET http://localhost:8000/company-info/{company_name}
```

#### 查询示例
```http
GET http://localhost:8000/examples
```

#### 政策分类
```http
GET http://localhost:8000/categories
```

### 文档管理

#### 上传政策文档
```http
POST http://localhost:8000/upload
Content-Type: multipart/form-data

file: [政策文档文件 - 支持PDF、DOCX、TXT]
```

## 响应格式

### 智能查询政策响应
```json
{
    "query": "我想查找和生物医药相关的政策",
    "total_results": 10,
    "results": [
        {
            "policy_id": "policy_001",
            "title": "生物医药产业发展扶持政策",
            "relevance_score": 0.95,
            "summary": "政策摘要",
            "key_points": ["支持生物医药企业发展", "最高200万元资金支持"],
            "applicability": {
                "行业匹配": "高度匹配",
                "规模匹配": "符合要求"
            },
            "requirements": ["企业注册成立", "具备研发能力"],
            "suggestions": ["准备企业资质材料", "完善研发项目计划"]
        }
    ],
    "processing_time": 0.283,
    "suggestions": ["相关政策较少，建议扩大查询范围"],
    "query_understanding": {
        "intent": "find_policy",
        "entities": {
            "industries": ["生物医药"],
            "enterprise_scales": [],
            "policy_types": []
        },
        "filters": {
            "industries": ["生物医药"]
        }
    }
}
```

### 自测通过率响应
```json
{
    "policy_id": "policy_157f44c2",
    "policy_title": "北京市高新技术企业认定政策",
    "company_name": "北京测试科技有限公司",
    "pass_rate": 43,
    "pass_level": "中",
    "analysis": {
        "met_conditions": [
            {
                "condition": "企业注册成立满一年",
                "status": "已满足", 
                "description": "企业成立于2023年1月，满足时间要求",
                "importance": "必要条件"
            }
        ],
        "pending_conditions": [
            {
                "condition": "研发费用占比达5%以上",
                "status": "待完善",
                "description": "当前研发费用占比为3%，需提升至5%以上",
                "importance": "重要条件"
            }
        ],
        "uncertain_conditions": []
    },
    "suggestions": [
        "提高研发投入占比至5%以上",
        "完善财务审计报告"
    ],
    "next_steps": [
        "制定研发费用提升计划",
        "联系会计师事务所进行审计"
    ],
    "processing_time": 0.156
}
```

### 一键匹配响应
```json
{
    "total_results": 15,
    "matches": [
        {
            "policy_id": "policy_001",
            "policy_name": "生物医药产业发展扶持政策",
            "match_score": 0.92,
            "match_level": "高",
            "key_description": "支持生物医药企业发展，给予最高200万元资金支持",
            "policy_type": "资金支持",
            "support_content": "研发费用补助、设备购置补贴",
            "application_conditions": "企业注册成立满一年，具备研发能力"
        }
    ],
    "processing_time": 0.85,
    "match_type": "basic",
    "suggestions": ["建议查看详细申请条件", "准备相关申请材料"]
}
```

## 配置选项

### 智能查询配置

#### 意图识别模式
- find_policy：政策查找
- check_eligibility：适用性检查
- get_funding：资金支持查询
- get_requirements：申请条件查询

#### 实体识别类型
- **行业类型**：生物医药、新一代信息技术、智能制造、先进能源、科技服务等
- **企业规模**：初创企业、小型企业、中型企业、大型企业
- **政策类型**：资金支持、税收优惠、人才政策、创新支持等
- **金额要求**：自动提取数值和单位
- **时间要求**：自动识别时间限制

#### 智能过滤规则
- prefer_startup_friendly：偏好初创企业友好政策
- exclude_high_barrier：排除高门槛政策
- industry_match：行业精确匹配
- scale_appropriate：企业规模适用性

### 自测通过率配置

#### 条件规则库
- **基础条件**：企业注册、经营范围、注册资本、合规经营
- **高新技术企业条件**：知识产权、研发人员占比、研发费用占比、高新技术产品收入占比、财务审计
- **资金支持类政策条件**：项目计划、配套资金、实施能力

#### 评分权重设置
- 必要条件：权重0.3-0.4
- 重要条件：权重0.2-0.3  
- 一般条件：权重0.1-0.2
- 加分条件：权重0.05-0.1

#### 通过率等级
- 高等级：≥70%（成功率较高）
- 中等级：40-69%（有一定成功可能）
- 低等级：<40%（需要大幅改进）

### 传统配置选项

#### 行业类型
- 生物医药（含医疗器械）
- 先进能源
- 智能制造
- 新一代信息技术
- 科技服务
- 其他

#### 企业规模
- 初创企业（成立<3年，员工<20人）
- 中小企业（员工20-200人）
- 大型企业（员工>200人）

#### 需求类型
- 资金补贴（如研发费用补助）
- 资质认定（如高新企业、专精特新）
- 人才支持（如落户、住房补贴）
- 空间/设备（如实验室租金减免）

## 系统特点

### 智能化程度高
- 🧠 **自然语言理解**：支持复杂中文查询和语义理解
- 🎯 **意图识别**：智能理解用户真实需求
- 🔍 **实体提取**：自动识别关键信息
- 📈 **查询扩展**：语义相似查询生成
- ⚖️ **动态权重**：根据查询复杂度调整算法权重

### 算法先进性
- 📊 **自测通过率算法**：科学评估申请成功率
- ⚖️ **权重评分系统**：基于条件重要性的评分
- 🎪 **混合检索引擎**：向量+关键词双重匹配
- 🔄 **智能融合算法**：RRF+意图加权
- 🚫 **智能排除**：初创企业查询自动排除高门槛政策

### 匹配精度高
- 🎪 **多维度算法**：行业+规模+需求综合匹配
- 🏢 **企业画像分析**：基于详细信息的深度理解
- ⚡ **动态评分**：实时调整匹配分数
- 🎚️ **智能过滤**：初创企业友好策略

### 用户体验好
- 🚀 **统一接口**：所有功能一个API解决
- 📊 **清晰展示**：高/中/低匹配度显示
- 💡 **个性化建议**：针对性申请建议和改进策略
- 📖 **自动文档**：FastAPI自动生成API文档

### 技术架构先进
- ⚡ **FastAPI框架**：高性能异步处理
- 🔧 **模块化设计**：组件独立可扩展
- 📚 **智能缓存**：提升响应速度
- 🛡️ **错误处理**：完善的异常机制

## 部署说明

### 环境要求
- Python 3.8+
- 依赖包见 requirements.txt

### 核心依赖
```
fastapi>=0.68.0
uvicorn>=0.15.0
sentence-transformers
torch
numpy
pydantic
requests
pymilvus  # 可选
```

### 安装步骤
```bash
# 1. 克隆项目
git clone <repository-url>
cd Policy-Match

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python start_production.py
```

### 性能优化
- ✅ 支持并发请求处理
- ✅ 模型预加载和缓存
- ✅ 智能查询优化
- ✅ 异步处理机制
- ✅ 智能算法权重调整
- ✅ 实时计算优化

## 监控和维护

### 健康检查
```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细系统状态
curl http://localhost:8000/status
```

### 性能监控
- **智能查询响应时间**：< 1秒（包含意图识别、实体提取、智能检索）
- **自测通过率计算**：< 0.5秒（包含条件分析、评分计算、建议生成）
- **一键匹配响应时间**：< 2秒（包含文档解析、检索、分析）
- 匹配准确率统计
- 系统资源使用监控
- 错误日志分析

### 扩展性
- 🔄 水平扩展支持
- 🔀 负载均衡兼容
- 📦 容器化部署就绪
- ☁️ 云服务集成友好

---

## 技术架构

```
                    政策匹配统一API系统
                           |
        ┌─────────────────────────────────────────┐
        │              FastAPI 服务层              │
        │    /search | /analyze-eligibility       │
        │    /basic-match | /precise-match        │
        └─────────────────────────────────────────┘
                           |
        ┌─────────────────────────────────────────┐
        │            PolicyMatcher              │
        │    (统一匹配引擎 + 通过率算法)          │
        └─────────────────────────────────────────┘
                           |
    ┌──────────┬──────────────────┬──────────────────┐
    │          │                  │                  │
┌─────────┐ ┌─────────┐    ┌─────────────┐  ┌─────────────┐
│智能查询  │ │自测通过率│    │检索引擎      │  │向量存储引擎  │
│理解模块  │ │算法模块  │    │             │  │             │
└─────────┘ └─────────┘    └─────────────┘  └─────────────┘
    │          │                  │                  │
    └──────────┼──────────────────┼──────────────────┘
               │                  │
        ┌─────────────┐    ┌─────────────┐
        │企业信息分析  │    │智能过滤引擎  │
        │    模块     │    │             │
        └─────────────┘    └─────────────┘
```

### 核心流程

1. **请求接收** → FastAPI路由分发
2. **智能解析** → 意图识别+实体提取（智能查询）/ 条件分析（自测算法）
3. **智能匹配** → 多维度匹配算法+智能过滤
4. **结果排序** → 相关性评分和智能排序
5. **响应生成** → 统一格式输出+个性化建议

## 使用案例

### 案例1：智能查询政策
```bash
# 复杂自然语言查询
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "我是一家小型初创企业，现阶段有什么政策比较适用",
    "top_k": 5
  }'

# 系统智能处理：
# - 意图识别：check_eligibility (置信度: 1.00)
# - 企业规模：初创企业、小型企业
# - 智能过滤：prefer_startup_friendly=True, exclude_high_barrier=True
# - 自动排除：大型企业专项基金、高营收要求政策
```

### 案例2：自测通过率算法
```bash
# 评估政策申请通过率
curl -X POST "http://localhost:8000/analyze-eligibility" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "policy_157f44c2",
    "company_info": {
      "company_name": "北京测试科技有限公司",
      "establishment_date": "2023-01-15",
      "rd_personnel_ratio": 60,
      "rd_expense_ratio": 8,
      "has_ip": true
    }
  }'

# 系统智能分析：
# - 条件匹配：逐项分析政策申请条件
# - 权重评分：基于条件重要性计算得分
# - 通过率计算：43%（中等级）
# - 改进建议：具体的条件完善建议
```

### 案例3：基础一键匹配
```bash
curl -X POST "http://localhost:8000/basic-match" \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "生物医药（含医疗器械）",
    "company_scale": "初创企业（成立<3年，员工<20人）",
    "demand_type": "资金补贴（如研发费用补助）"
  }'
```

### 案例4：精准匹配
基于企业详细信息进行深度分析，提供最精准的政策匹配建议。

---

## 功能演示

### 智能查询功能演示
```bash
# 完整智能查询功能演示
python demo_intelligent_query.py

# 演示内容：
# 1. 查询理解功能演示
# 2. 智能过滤功能演示  
# 3. 真实查询处理演示
# 4. API使用示例
```

### 自测通过率算法演示
```bash
# 自测通过率算法完整演示
python demo_eligibility.py

# 演示内容：
# 1. 企业信息展示
# 2. 条件分析过程
# 3. 通过率计算
# 4. 改进建议生成
# 5. 改进前后效果对比
```

### 完整测试验证
```bash
# 自测通过率算法测试
python test_eligibility.py

# 测试覆盖：
# - 条件较好企业：70%通过率（高等级）
# - 条件一般企业：10%通过率（低等级）
# - 条件优秀企业：70%通过率（高等级）
# - 边界情况处理
```

---

## 📞 联系支持

如有问题或建议，请通过以下方式联系：
- 📧 技术支持：support@example.com
- 📝 问题反馈：GitHub Issues
- 📖 文档更新：定期维护

**系统版本**: 3.0.0 - 智能化全面升级版  
**最后更新**: 2025年1月  
**维护状态**: ✅ 积极维护中

### 新版本特性
- ✨ **智能查询政策**：自然语言理解+意图识别+实体提取+智能过滤
- 📊 **自测通过率算法**：科学评估+条件分析+个性化建议  
- 🧠 **高级NLU引擎**：支持复杂中文查询表达和语义理解
- ⚖️ **权重评分系统**：基于条件重要性的科学评分算法
- 🎯 **智能过滤机制**：初创企业友好+排除高门槛政策
- 🚀 **性能优化**：响应时间大幅提升，支持实时计算 