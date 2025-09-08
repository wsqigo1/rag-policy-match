from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

class PolicyChunk(BaseModel):
    """政策文档分块模型"""
    chunk_id: str = Field(..., description="分块唯一标识")
    policy_id: str = Field(..., description="政策文档ID")
    content: str = Field(..., description="分块内容")
    chunk_type: str = Field(default="text", description="分块类型：text/table/image")
    section: Optional[str] = Field(None, description="所属章节")
    page_num: Optional[int] = Field(None, description="页码")
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    # 🆕 新增结构化字段
    # 政策基础信息
    basis_document: Optional[str] = Field(None, description="依据文件")
    issuing_agency: Optional[str] = Field(None, description="发文机构")
    document_number: Optional[str] = Field(None, description="发文字号")
    issue_date: Optional[str] = Field(None, description="发布日期")
    
    # 政策分类和服务
    tool_category: Optional[str] = Field(None, description="工具分类")
    service_object: Optional[str] = Field(None, description="服务对象")
    service_content: Optional[str] = Field(None, description="服务内容")
    
    # 条件和流程
    condition_requirements: Optional[str] = Field(None, description="条件要求")
    service_process: Optional[str] = Field(None, description="服务流程")
    time_frequency: Optional[str] = Field(None, description="时间/频度")
    contact_info: Optional[str] = Field(None, description="联络方式")
    
    # 分析和匹配相关
    policy_level: Optional[str] = Field(None, description="政策级别（国家/市级/区级）")
    support_amount: Optional[str] = Field(None, description="支持金额")
    application_deadline: Optional[str] = Field(None, description="申请截止时间")

class PolicyDocument(BaseModel):
    """政策文档模型"""
    policy_id: str = Field(..., description="政策ID")
    title: str = Field(..., description="政策标题")
    content: str = Field(..., description="政策全文")
    policy_type: Optional[str] = Field(None, description="政策类型")
    industry: List[str] = Field(default_factory=list, description="适用行业")
    enterprise_scale: List[str] = Field(default_factory=list, description="适用企业规模")
    regions: List[str] = Field(default_factory=list, description="适用地区")
    effective_date: Optional[datetime] = Field(None, description="生效时间")
    expire_date: Optional[datetime] = Field(None, description="失效时间")
    source_url: Optional[str] = Field(None, description="来源链接")
    file_path: str = Field(..., description="文件路径")
    chunks: List[PolicyChunk] = Field(default_factory=list, description="文档分块")
    
    # 🆕 添加用于数据库关联的字段
    original_filename: Optional[str] = Field(None, description="原始文件名")
    document_number: Optional[str] = Field(None, description="发文字号")
    issuing_agency: Optional[str] = Field(None, description="发文机构")

# ======= 一键匹配相关数据模型 =======

class BasicMatchRequest(BaseModel):
    """基础匹配请求模型"""
    industry: str = Field(..., description="企业所属行业")
    company_scale: str = Field(..., description="企业规模")
    demand_type: str = Field(..., description="需求类型")

class CompanyInfo(BaseModel):
    """企业信息模型"""
    company_name: str = Field(..., description="企业名称")
    industry: Optional[str] = Field(None, description="所属行业")
    scale: Optional[str] = Field(None, description="企业规模")
    employees: Optional[int] = Field(None, description="员工数")
    registered_capital: Optional[float] = Field(None, description="注册资本（万元）")
    annual_revenue: Optional[float] = Field(None, description="年营业额（万元）")
    enterprise_type: Optional[str] = Field(None, description="企业性质")
    location: Optional[str] = Field(None, description="企业所在地")
    established_year: Optional[int] = Field(None, description="成立年份")
    
    # 兼容旧字段
    company_type: Optional[str] = Field(None, description="企业类型")
    establishment_date: Optional[str] = Field(None, description="成立时间 YYYY-MM-DD")
    registered_address: Optional[str] = Field(None, description="注册地址")
    business_scope: Optional[str] = Field(None, description="经营范围")
    honors_qualifications: List[str] = Field(default_factory=list, description="已获得的荣誉资质")

class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="查询文本", min_length=1, max_length=500)
    industry: Optional[str] = Field(None, description="行业筛选")
    enterprise_scale: Optional[str] = Field(None, description="企业规模筛选")
    policy_type: Optional[str] = Field(None, description="政策类型筛选")
    region: Optional[str] = Field(None, description="地区筛选")
    top_k: int = Field(default=10, description="返回结果数量", ge=1, le=50)
    
    # 🆕 新增字段 - 支持个性化查询
    company_info: Optional[CompanyInfo] = Field(None, description="企业信息，用于个性化推荐")

class PreciseMatchRequest(BaseModel):
    """精准匹配请求模型"""
    basic_request: BasicMatchRequest = Field(..., description="基础匹配参数")
    company_info: CompanyInfo = Field(..., description="企业详细信息")

class PolicyMatch(BaseModel):
    """政策匹配结果模型"""
    policy_id: str = Field(..., description="政策ID")
    policy_name: str = Field(..., description="政策名称")
    match_score: float = Field(..., description="匹配分数 0-1", ge=0, le=1)
    match_level: str = Field(..., description="匹配度等级：高/中/低")
    key_description: str = Field(..., description="关键描述（150字以内）")
    policy_type: str = Field(..., description="政策类型")
    support_content: str = Field(..., description="支持内容")
    application_conditions: str = Field(..., description="申请条件")
    
    # 🆕 添加用于数据库关联的字段
    original_filename: Optional[str] = Field(None, description="原始文件名")
    file_path: Optional[str] = Field(None, description="文件路径")
    document_number: Optional[str] = Field(None, description="发文字号")
    issuing_agency: Optional[str] = Field(None, description="发文机构")

class OneClickMatchResponse(BaseModel):
    """一键匹配响应模型"""
    total_results: int = Field(..., description="结果总数")
    matches: List[PolicyMatch] = Field(..., description="匹配结果列表")
    processing_time: float = Field(..., description="处理时间(秒)")
    match_type: str = Field(..., description="匹配类型：basic/precise")
    suggestions: List[str] = Field(default_factory=list, description="建议列表")

# ======= 原有数据模型 =======

class MatchResult(BaseModel):
    """匹配结果模型"""
    policy_id: str = Field(..., description="政策ID")
    title: str = Field(..., description="政策标题")
    relevance_score: float = Field(..., description="相关性得分", ge=0, le=1)
    matched_chunks: List[str] = Field(..., description="匹配的文档分块")
    summary: str = Field(..., description="政策摘要")
    key_points: List[str] = Field(default_factory=list, description="核心要点")
    applicability: Dict[str, str] = Field(default_factory=dict, description="适用性分析")
    requirements: List[str] = Field(default_factory=list, description="申请条件")
    suggestions: List[str] = Field(default_factory=list, description="申请建议")

class RetrievalResult(BaseModel):
    """检索结果模型"""
    chunk_id: str
    content: str
    score: float
    policy_id: str
    title: Optional[str] = Field(None, description="政策标题")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class QueryResponse(BaseModel):
    """查询响应模型"""
    query: Optional[str] = Field(None, description="原始查询")
    total_results: Optional[int] = Field(None, description="总结果数")
    results: List[RetrievalResult] = Field(default_factory=list, description="匹配结果列表")
    processing_time: float = Field(..., description="处理时间(秒)")
    suggestions: List[str] = Field(default_factory=list, description="查询建议")
    
    # 🆕 新增字段 - 支持增强查询
    query_analysis: Optional[Dict[str, Any]] = Field(None, description="查询分析结果")
    personalized_summary: Optional[str] = Field(None, description="个性化推荐摘要")
    total_found: Optional[int] = Field(None, description="找到的政策总数")

class EmbeddingRequest(BaseModel):
    """向量化请求模型"""
    texts: List[str] = Field(..., description="待向量化文本列表")
    batch_size: int = Field(default=32, description="批处理大小")

class SystemStatus(BaseModel):
    """系统状态模型"""
    status: str = Field(..., description="系统状态")
    total_policies: int = Field(..., description="政策总数")
    total_chunks: int = Field(..., description="分块总数")
    vector_store_status: str = Field(..., description="向量库状态")
    elasticsearch_status: str = Field(..., description="ES状态")
    last_update: datetime = Field(..., description="最后更新时间")


# ======= 自测通过率相关数据模型 =======

class RequirementStatus(BaseModel):
    """申请条件状态模型"""
    condition: str = Field(..., description="申请条件描述")
    status: str = Field(..., description="状态：已满足/待完善/不确定")
    details: str = Field(..., description="详细说明")
    importance: str = Field(..., description="重要性：必要条件/加分项/一般要求")


class ConditionAnalysis(BaseModel):
    """条件分析模型"""
    satisfied_conditions: List[RequirementStatus] = Field(default_factory=list, description="已满足条件")
    pending_conditions: List[RequirementStatus] = Field(default_factory=list, description="待完善条件")
    unknown_conditions: List[RequirementStatus] = Field(default_factory=list, description="不确定条件")


class PolicyEligibilityRequest(BaseModel):
    """政策资格自测请求模型"""
    policy_id: str = Field(..., description="政策ID")
    company_info: CompanyInfo = Field(..., description="企业详细信息")
    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="补充信息，如研发费用、高新收入等")
    
    # 🆕 新增字段 - 对应政策结构化信息
    target_service_object: Optional[str] = Field(None, description="目标服务对象")
    requested_tool_category: Optional[str] = Field(None, description="请求的工具分类")
    preferred_support_amount: Optional[float] = Field(None, description="期望支持金额")

@dataclass
class StructuredPolicy:
    """结构化政策信息"""
    policy_id: str
    title: str
    
    # 基础信息字段
    basis_document: Optional[str] = None      # 依据文件
    issuing_agency: Optional[str] = None      # 发文机构  
    document_number: Optional[str] = None     # 发文字号
    issue_date: Optional[str] = None          # 发布日期
    
    # 分类和服务字段
    tool_category: Optional[str] = None       # 工具分类（资金支持、政策支持等）
    service_object: Optional[str] = None      # 服务对象
    service_content: Optional[str] = None     # 服务内容
    
    # 条件和流程字段
    condition_requirements: Optional[str] = None   # 条件要求
    service_process: Optional[str] = None          # 服务流程  
    time_frequency: Optional[str] = None           # 时间/频度
    contact_info: Optional[str] = None             # 联络方式
    
    # 解析出的关键信息
    industries: Optional[List[str]] = None          # 适用行业
    enterprise_scales: Optional[List[str]] = None  # 企业规模
    policy_types: Optional[List[str]] = None       # 政策类型
    support_amount_range: Optional[Dict] = None    # 支持金额范围
    
    # 完整内容
    full_content: Optional[str] = None
    chunks: Optional[List[PolicyChunk]] = None
    
    # 🆕 添加用于数据库关联的字段
    original_filename: Optional[str] = None    # 原始文件名
    file_path: Optional[str] = None            # 文件路径

@dataclass
class EnhancedRequirementStatus:
    """增强的申请条件状态"""
    condition: str
    status: str  # "满足"/"待完善"/"不确定"
    description: str
    importance: float  # 重要性权重 (0.0-1.0)
    
    # 🆕 新增字段 - 与结构化政策字段对应
    source_field: Optional[str] = None        # 来源字段（condition_requirements/service_object等）
    requirement_type: Optional[str] = None    # 要求类型（基础条件/资格条件/材料条件等）
    verification_method: Optional[str] = None # 验证方式
    improvement_suggestion: Optional[str] = None # 改进建议

class PolicyEligibilityResponse(BaseModel):
    """政策资格自测响应模型"""
    policy_id: str = Field(..., description="政策ID")
    policy_name: str = Field(..., description="政策名称")
    policy_type: str = Field(..., description="政策类型")
    support_amount: str = Field(..., description="支持金额/内容")
    pass_rate: int = Field(..., description="预估通过率百分比", ge=0, le=100)
    pass_level: str = Field(..., description="通过率等级：高/中/低")
    condition_analysis: ConditionAnalysis = Field(..., description="条件分析")
    suggestions: List[str] = Field(default_factory=list, description="优化建议")
    processing_time: float = Field(..., description="分析时间（秒）")
    
    # 🆕 增强字段
    policy_info: Optional[StructuredPolicy] = Field(None, description="政策信息")
    detailed_analysis: Optional[Dict[str, Any]] = Field(None, description="详细分析")
    matching_score: Optional[float] = Field(None, description="整体匹配分数")
    feasibility_assessment: Optional[str] = Field(None, description="可行性评估")
    timeline_estimate: Optional[str] = Field(None, description="时间线估计")
    risk_factors: Optional[List[str]] = Field(None, description="风险因素")
    
    # 🆕 添加用于数据库关联的字段
    original_filename: Optional[str] = Field(None, description="原始文件名")
    file_path: Optional[str] = Field(None, description="文件路径")
    document_number: Optional[str] = Field(None, description="发文字号")
    issuing_agency: Optional[str] = Field(None, description="发文机构")

# ======= 企业发展数据政策匹配相关数据模型 =======

class CompanyDevelopmentDataRequest(BaseModel):
    """普遍企业发展数据政策匹配请求模型"""
    company_name: str = Field(..., description="企业名称")
    report_period: int = Field(..., description="填报周期，格式为YYYYMM")
    industrial_output: float = Field(..., description="工业总产值（千元）", ge=0)
    total_income: float = Field(..., description="总收入(千元)", ge=0)
    tech_income: float = Field(..., description="技术收入(千元)", ge=0)
    tax_payment: float = Field(..., description="实缴税费总额(千元)", ge=0)
    profit_total: float = Field(..., description="利润总额(千元)")
    export_total: float = Field(..., description="出口总额(千元)", ge=0)
    rd_personnel_count: int = Field(..., description="研究开发人员合计(人)", ge=0)
    rd_expense: float = Field(..., description="研究开发费用合计(千元)", ge=0)
    valid_patent_count: int = Field(..., description="拥有有效专利数（个）", ge=0)
    valid_invention_patent_count: int = Field(..., description="有效发明专利数（个）", ge=0)
    employee_count: int = Field(..., description="从业人员数（人）", ge=1)

class MajorEnterpriseDataRequest(BaseModel):
    """规上企业发展数据政策匹配请求模型"""
    company_name: str = Field(..., description="企业名称")
    report_period: int = Field(..., description="填报周期，格式为YYYYMM")
    total_income: float = Field(..., description="总收入(万元)", ge=0)
    industrial_output: float = Field(..., description="工业总产值(万元)", ge=0)
    tax_payment: float = Field(..., description="实缴税费(万元)", ge=0)
    profit_total: float = Field(..., description="利润总额(万元)")
    export_total: float = Field(..., description="出口总额(万元)", ge=0)
    rd_expense: float = Field(..., description="研发费用(万元)", ge=0)
    employee_count: int = Field(..., description="从业人员(人)", ge=1)
    rd_personnel_count: int = Field(..., description="研发人员(人)", ge=0)

class DevelopmentDataMatch(BaseModel):
    """企业发展数据政策匹配结果模型"""
    policy_id: str = Field(..., description="政策ID")
    policy_name: str = Field(..., description="政策名称")
    match_score: float = Field(..., description="匹配分数 0-1", ge=0, le=1)
    match_level: str = Field(..., description="匹配度等级：高/中/低")
    policy_type: str = Field(..., description="政策类型")
    support_content: str = Field(..., description="支持内容")
    key_requirements: List[str] = Field(default_factory=list, description="关键要求")
    matching_indicators: Dict[str, Any] = Field(default_factory=dict, description="匹配指标分析")
    feasibility_analysis: str = Field(..., description="可行性分析")
    application_priority: str = Field(..., description="申请优先级：高/中/低")

    # 继承自PolicyMatch的字段以保持兼容性
    original_filename: Optional[str] = Field(None, description="原始文件名")
    file_path: Optional[str] = Field(None, description="文件路径")
    document_number: Optional[str] = Field(None, description="发文字号")
    issuing_agency: Optional[str] = Field(None, description="发文机构")

class DevelopmentDataMatchResponse(BaseModel):
    """企业发展数据政策匹配响应模型"""
    company_name: str = Field(..., description="企业名称")
    report_period: int = Field(..., description="填报周期")
    total_results: int = Field(..., description="匹配结果总数")
    matches: List[DevelopmentDataMatch] = Field(..., description="匹配结果列表")
    processing_time: float = Field(..., description="处理时间(秒)")
    match_type: str = Field(..., description="匹配类型：development_data")

    # 企业数据分析概览
    company_analysis: Dict[str, Any] = Field(default_factory=dict, description="企业数据分析概览")
    strengths: List[str] = Field(default_factory=list, description="企业优势")
    improvement_areas: List[str] = Field(default_factory=list, description="改进领域")
    recommendations: List[str] = Field(default_factory=list, description="政策申请建议")