import logging
import time
import re
from typing import List, Dict, Any
from collections import defaultdict

from models import QueryRequest, QueryResponse, MatchResult, RetrievalResult

logger = logging.getLogger(__name__)

class PolicyMatcher:
    """政策匹配核心引擎"""
    
    def __init__(self):
        self._retriever = None
        self._document_processor = None
        self._embedding_manager = None
        self._vector_store = None
        
        # 政策文档缓存
        self._policy_cache = {}
    
    @property
    def retriever(self):
        """延迟加载retriever"""
        if self._retriever is None:
            from retriever import retriever
            self._retriever = retriever
        return self._retriever
    
    @property
    def document_processor(self):
        """延迟加载document_processor"""
        if self._document_processor is None:
            from document_processor import DocumentProcessor
            self._document_processor = DocumentProcessor()
        return self._document_processor
    
    @property
    def embedding_manager(self):
        """延迟加载embedding_manager"""
        if self._embedding_manager is None:
            from embeddings import embedding_manager
            self._embedding_manager = embedding_manager
        return self._embedding_manager
    
    @property
    def vector_store(self):
        """延迟加载vector_store"""
        if self._vector_store is None:
            from vector_store import vector_store
            self._vector_store = vector_store
        return self._vector_store

    def match_policies(self, query_request: QueryRequest) -> QueryResponse:
        """
        政策匹配主函数
        
        Args:
            query_request: 查询请求
            
        Returns:
            查询响应结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始政策匹配: {query_request.query}")
            
            # 1. 执行检索
            retrieval_results = self.retriever.retrieve(query_request)
            
            # 2. 聚合和分析结果
            match_results = self._aggregate_results(retrieval_results, query_request)
            
            # 3. 生成匹配分析
            analyzed_results = self._analyze_matches(match_results, query_request)
            
            # 4. 生成查询建议
            suggestions = self._generate_suggestions(query_request, analyzed_results)
            
            processing_time = time.time() - start_time
            
            response = QueryResponse(
                query=query_request.query,
                total_results=len(analyzed_results),
                results=analyzed_results,
                processing_time=processing_time,
                suggestions=suggestions
            )
            
            logger.info(f"政策匹配完成，耗时: {processing_time:.2f}秒，返回: {len(analyzed_results)}个结果")
            return response
            
        except Exception as e:
            logger.error(f"政策匹配失败: {e}")
            return QueryResponse(
                query=query_request.query,
                total_results=0,
                results=[],
                processing_time=time.time() - start_time,
                suggestions=["请检查查询条件或联系管理员"]
            )
    
    def _aggregate_results(self, retrieval_results: List[RetrievalResult], 
                          query_request: QueryRequest) -> List[MatchResult]:
        """聚合检索结果到政策级别"""
        try:
            # 按政策ID聚合结果
            policy_groups = defaultdict(list)
            for result in retrieval_results:
                policy_groups[result.policy_id].append(result)
            
            match_results = []
            
            for policy_id, chunks in policy_groups.items():
                # 计算政策级别的相关性分数
                relevance_score = self._calculate_policy_score(chunks)
                
                # 获取政策标题
                title = self._get_policy_title(chunks)
                
                # 提取匹配的分块内容
                matched_chunks = [chunk.content for chunk in chunks[:3]]  # 最多取3个分块
                
                # 生成政策摘要
                summary = self._generate_policy_summary(chunks, query_request.query)
                
                match_result = MatchResult(
                    policy_id=policy_id,
                    title=title,
                    relevance_score=relevance_score,
                    matched_chunks=matched_chunks,
                    summary=summary
                )
                
                match_results.append(match_result)
            
            # 按相关性分数排序
            match_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            return match_results[:query_request.top_k]
            
        except Exception as e:
            logger.error(f"结果聚合失败: {e}")
            return []
    
    def _calculate_policy_score(self, chunks: List[RetrievalResult]) -> float:
        """计算政策级别的相关性分数"""
        if not chunks:
            return 0.0
        
        # 使用加权平均，权重递减
        weights = [1.0, 0.8, 0.6, 0.4, 0.2]
        total_score = 0.0
        total_weight = 0.0
        
        for i, chunk in enumerate(chunks[:5]):
            weight = weights[i] if i < len(weights) else 0.1
            total_score += chunk.score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _get_policy_title(self, chunks: List[RetrievalResult]) -> str:
        """获取政策标题"""
        if not chunks:
            return "未知政策"
        
        # 优先从元数据中获取标题
        for chunk in chunks:
            if 'title' in chunk.metadata and chunk.metadata['title']:
                return chunk.metadata['title']
        
        # 如果没有标题，使用政策ID
        return f"政策文档 {chunks[0].policy_id}"
    
    def _generate_policy_summary(self, chunks: List[RetrievalResult], query: str) -> str:
        """生成政策摘要"""
        try:
            # 合并相关分块内容
            combined_content = " ".join([chunk.content for chunk in chunks[:3]])
            
            # 提取关键信息
            key_info = self._extract_key_information(combined_content, query)
            
            # 生成简洁摘要
            summary_parts = []
            
            if key_info.get('policy_type'):
                summary_parts.append(f"政策类型：{key_info['policy_type']}")
            
            if key_info.get('benefits'):
                summary_parts.append(f"主要内容：{key_info['benefits'][:100]}...")
            
            if key_info.get('conditions'):
                summary_parts.append(f"适用条件：{key_info['conditions'][:100]}...")
            
            return " | ".join(summary_parts) if summary_parts else combined_content[:200] + "..."
            
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            return chunks[0].content[:200] + "..." if chunks else ""
    
    def _extract_key_information(self, content: str, query: str) -> Dict[str, str]:
        """提取关键信息"""
        key_info = {}
        
        # 提取政策类型
        for policy_type, keywords in {
            "资金支持": ["补贴", "资助", "奖励", "专项资金"],
            "税收优惠": ["税收", "减税", "免税", "优惠"],
            "人才政策": ["人才", "专家", "引进", "培养"],
            "创新支持": ["创新", "研发", "技术", "专利"],
            "产业扶持": ["产业", "制造", "升级", "转型"]
        }.items():
            if any(keyword in content for keyword in keywords):
                key_info['policy_type'] = policy_type
                break
        
        # 提取支持内容
        benefit_patterns = [
            r'给予.{1,50}[补贴资助奖励支持]',
            r'最高.{1,30}万元',
            r'按照.{1,50}比例',
            r'享受.{1,50}优惠'
        ]
        
        benefits = []
        for pattern in benefit_patterns:
            matches = re.findall(pattern, content)
            benefits.extend(matches)
        
        key_info['benefits'] = "；".join(benefits[:3])
        
        # 提取申请条件
        condition_patterns = [
            r'[需要应当必须].{1,80}',
            r'申请条件.{1,100}',
            r'适用范围.{1,100}'
        ]
        
        conditions = []
        for pattern in condition_patterns:
            matches = re.findall(pattern, content)
            conditions.extend(matches)
        
        key_info['conditions'] = "；".join(conditions[:2])
        
        return key_info
    
    def _analyze_matches(self, match_results: List[MatchResult], 
                        query_request: QueryRequest) -> List[MatchResult]:
        """分析匹配结果，添加详细信息"""
        try:
            for match in match_results:
                # 分析适用性
                match.applicability = self._analyze_applicability(match, query_request)
                
                # 提取核心要点
                match.key_points = self._extract_key_points(match.matched_chunks)
                
                # 提取申请条件
                match.requirements = self._extract_requirements(match.matched_chunks)
                
                # 生成申请建议
                match.suggestions = self._generate_application_suggestions(match, query_request)
            
            return match_results
            
        except Exception as e:
            logger.error(f"结果分析失败: {e}")
            return match_results
    
    def _analyze_applicability(self, match: MatchResult, 
                             query_request: QueryRequest) -> Dict[str, str]:
        """分析适用性"""
        applicability = {}
        
        combined_content = " ".join(match.matched_chunks).lower()
        
        # 行业匹配分析
        if query_request.industry:
            if query_request.industry.lower() in combined_content:
                applicability['行业匹配'] = "高度匹配"
            else:
                # 检查同义词
                from config import config
                matched = False
                for industry, keywords in config.INDUSTRY_MAPPING.items():
                    if query_request.industry in keywords:
                        for keyword in keywords:
                            if keyword in combined_content:
                                applicability['行业匹配'] = "相关匹配"
                                matched = True
                                break
                        if matched:
                            break
                
                if not matched:
                    applicability['行业匹配'] = "需要进一步确认"
        
        # 企业规模匹配分析
        detected_scale = self._detect_enterprise_scale_in_content(combined_content)
        if detected_scale:
            if query_request.enterprise_scale and query_request.enterprise_scale in detected_scale:
                applicability['规模匹配'] = "符合要求"
            else:
                applicability['规模匹配'] = f"适用于{detected_scale}"
        else:
            applicability['规模匹配'] = "无特殊限制"
        
        # 匹配度评估
        if match.relevance_score > 0.8:
            applicability['总体评估'] = "高度推荐"
        elif match.relevance_score > 0.6:
            applicability['总体评估'] = "推荐申请"
        else:
            applicability['总体评估'] = "可以考虑"
        
        return applicability
    
    def _detect_enterprise_scale_in_content(self, content: str) -> str:
        """检测内容中的企业规模要求"""
        scale_indicators = {
            "大型企业": ["大型企业", "规模以上", "上市公司", "年营收.*亿", "员工.*千人以上"],
            "中型企业": ["中型企业", "中等规模", "年营收.*千万"],
            "小型企业": ["小型企业", "小微企业", "中小企业"],
            "初创企业": ["初创", "新成立", "创业", "起步阶段"]
        }
        
        for scale, indicators in scale_indicators.items():
            for indicator in indicators:
                if re.search(indicator, content):
                    return scale
        
        return ""
    
    def _extract_key_points(self, chunks: List[str]) -> List[str]:
        """提取核心要点"""
        key_points = []
        
        combined_content = " ".join(chunks)
        
        # 支持内容要点
        support_patterns = [
            r'给予.{1,60}[补贴资助奖励支持]',
            r'最高[不超过]*\s*.{1,30}万元',
            r'按照.{1,50}比例[给予补贴支持]',
            r'享受.{1,50}[优惠政策]',
            r'[免减].*税收'
        ]
        
        for pattern in support_patterns:
            matches = re.findall(pattern, combined_content)
            key_points.extend([match.strip() for match in matches if len(match.strip()) > 10])
        
        # 去重并限制数量
        unique_points = list(dict.fromkeys(key_points))
        return unique_points[:5]
    
    def _extract_requirements(self, chunks: List[str]) -> List[str]:
        """提取申请条件"""
        requirements = []
        
        combined_content = " ".join(chunks)
        
        # 条件模式
        requirement_patterns = [
            r'申请条件[：:].{1,100}',
            r'[需要应当必须].{10,80}',
            r'[符合满足].*条件.{1,60}',
            r'注册.*[年时间].{1,30}',
            r'年营收.*[万元亿元].{1,30}'
        ]
        
        for pattern in requirement_patterns:
            matches = re.findall(pattern, combined_content)
            requirements.extend([match.strip() for match in matches])
        
        # 清理和去重
        cleaned_requirements = []
        for req in requirements:
            if len(req) > 10 and len(req) < 200:
                cleaned_requirements.append(req)
        
        return list(dict.fromkeys(cleaned_requirements))[:5]
    
    def _generate_application_suggestions(self, match: MatchResult, 
                                        query_request: QueryRequest) -> List[str]:
        """生成申请建议"""
        suggestions = []
        
        # 基于匹配度的建议
        if match.relevance_score > 0.8:
            suggestions.append("建议优先申请此政策，匹配度很高")
        elif match.relevance_score > 0.6:
            suggestions.append("建议详细了解申请条件，符合要求可申请")
        else:
            suggestions.append("建议先确认是否符合申请条件")
        
        # 基于企业规模的建议
        if query_request.enterprise_scale == "初创企业":
            suggestions.append("作为初创企业，建议重点关注门槛较低的政策")
            suggestions.append("可先申请相关认定资质，为后续政策申请做准备")
        
        # 基于查询内容的建议
        query_lower = query_request.query.lower()
        if "资金" in query_lower or "补贴" in query_lower:
            suggestions.append("建议准备详细的资金使用计划和预算")
        
        if "创新" in query_lower or "研发" in query_lower:
            suggestions.append("建议整理相关技术文档和研发成果证明")
        
        return suggestions[:3]
    
    def _generate_suggestions(self, query_request: QueryRequest, 
                            results: List[MatchResult]) -> List[str]:
        """生成查询建议"""
        suggestions = []
        
        if not results:
            suggestions.append("未找到匹配的政策，建议：")
            suggestions.append("1. 调整查询关键词，使用更通用的表述")
            suggestions.append("2. 尝试按行业或政策类型分类查询")
            return suggestions
        
        if len(results) < 3:
            suggestions.append("相关政策较少，建议：")
            suggestions.append("1. 扩大查询范围，考虑相关行业政策")
            suggestions.append("2. 关注上级政府的通用性政策")
        
        # 基于查询内容的建议
        query_lower = query_request.query.lower()
        
        if not any(scale in query_lower for scale in ["初创", "小型", "中型", "大型"]):
            suggestions.append("建议明确企业规模，以获得更精准的政策匹配")
        
        if not any(industry in query_lower for industry in ["生物", "医药", "信息", "新能源", "新材料"]):
            suggestions.append("建议指定行业领域，以获得更相关的政策推荐")
        
        return suggestions[:3]
    
    def add_policy_document(self, file_path: str) -> bool:
        """添加政策文档到系统"""
        try:
            logger.info(f"开始添加政策文档: {file_path}")
            
            # 1. 处理文档
            policy_doc = self.document_processor.process_document(file_path)
            
            # 2. 生成向量
            chunk_texts = [chunk.content for chunk in policy_doc.chunks]
            embeddings = self.embedding_manager.encode_texts(chunk_texts)
            
            # 3. 存储到向量库
            policy_metadata = {
                'industries': policy_doc.industry,
                'enterprise_scales': policy_doc.enterprise_scale,
                'policy_types': [policy_doc.policy_type] if policy_doc.policy_type else []
            }
            
            success = self.vector_store.store_policy_chunks(
                policy_doc.chunks,
                embeddings,
                policy_doc.title,
                policy_metadata
            )
            
            if success:
                logger.info(f"政策文档添加成功: {file_path}")
                return True
            else:
                logger.error(f"政策文档存储失败: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"添加政策文档失败: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            vector_status = self.vector_store.get_status()
            embedding_status = self.embedding_manager.get_model_info()
            
            return {
                "status": "运行中",
                "vector_store": vector_status,
                "embedding_model": embedding_status,
                "components": {
                    "document_processor": "正常",
                    "retriever": "正常",
                    "matcher": "正常"
                }
            }
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {"status": "异常", "error": str(e)}

# 延迟创建全局政策匹配引擎实例
_policy_matcher = None

def get_policy_matcher():
    """获取政策匹配引擎实例"""
    global _policy_matcher
    if _policy_matcher is None:
        _policy_matcher = PolicyMatcher()
    return _policy_matcher

# 为了向后兼容，提供policy_matcher属性
def __getattr__(name):
    if name == 'policy_matcher':
        return get_policy_matcher()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 