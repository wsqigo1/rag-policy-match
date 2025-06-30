from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

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

class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="查询文本", min_length=1, max_length=500)
    industry: Optional[str] = Field(None, description="行业筛选")
    enterprise_scale: Optional[str] = Field(None, description="企业规模筛选")
    policy_type: Optional[str] = Field(None, description="政策类型筛选")
    region: Optional[str] = Field(None, description="地区筛选")
    top_k: int = Field(default=10, description="返回结果数量", ge=1, le=50)

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

class QueryResponse(BaseModel):
    """查询响应模型"""
    query: str = Field(..., description="原始查询")
    total_results: int = Field(..., description="总结果数")
    results: List[MatchResult] = Field(..., description="匹配结果列表")
    processing_time: float = Field(..., description="处理时间(秒)")
    suggestions: List[str] = Field(default_factory=list, description="查询建议")

class RetrievalResult(BaseModel):
    """检索结果模型"""
    chunk_id: str
    content: str
    score: float
    policy_id: str
    metadata: Dict[str, Any]

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