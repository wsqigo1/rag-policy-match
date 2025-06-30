import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import re

from models import RetrievalResult, QueryRequest
from config import config

logger = logging.getLogger(__name__)

class HybridRetriever:
    """混合检索引擎"""
    
    def __init__(self):
        self._embedding_manager = None
        self._vector_store = None
    
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
    
    def retrieve(self, query_request: QueryRequest) -> List[RetrievalResult]:
        """
        混合检索主函数
        
        Args:
            query_request: 查询请求对象
            
        Returns:
            检索结果列表
        """
        logger.info(f"开始混合检索: {query_request.query}")
        
        try:
            # 1. 查询预处理和扩展
            processed_query, expanded_queries = self._preprocess_query(query_request.query)
            
            # 2. 构建过滤条件
            filters = self._build_filters(query_request)
            
            # 3. 向量检索
            vector_results = self._vector_search(processed_query, query_request.top_k * 2, filters)
            
            # 4. 关键词检索
            keyword_results = self._keyword_search(expanded_queries, query_request.top_k * 2, filters)
            
            # 5. 融合结果
            final_results = self._fusion_results(vector_results, keyword_results, query_request.top_k)
            
            # 6. 后处理
            processed_results = self._post_process_results(final_results, query_request)
            
            logger.info(f"检索完成，返回 {len(processed_results)} 个结果")
            return processed_results
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []
    
    def _preprocess_query(self, query: str) -> Tuple[str, List[str]]:
        """查询预处理和扩展"""
        # 清理查询文本
        processed_query = re.sub(r'[^\w\s]', ' ', query)
        processed_query = ' '.join(processed_query.split())
        
        # 查询扩展
        expanded_queries = self.embedding_manager.expand_query(processed_query)
        
        logger.info(f"查询扩展: {query} -> {expanded_queries}")
        return processed_query, expanded_queries
    
    def _build_filters(self, query_request: QueryRequest) -> Dict[str, Any]:
        """构建过滤条件"""
        filters = {}
        
        # 行业过滤
        if query_request.industry:
            # 检查是否有映射的同义行业
            mapped_industries = []
            for industry, keywords in config.INDUSTRY_MAPPING.items():
                if query_request.industry in keywords or query_request.industry == industry:
                    mapped_industries.append(industry)
            
            if mapped_industries:
                filters['industries'] = mapped_industries
            else:
                filters['industries'] = [query_request.industry]
        
        # 企业规模过滤
        if query_request.enterprise_scale:
            mapped_scales = []
            for scale, keywords in config.ENTERPRISE_SCALES.items():
                if query_request.enterprise_scale in keywords or query_request.enterprise_scale == scale:
                    mapped_scales.append(scale)
            
            if mapped_scales:
                filters['enterprise_scales'] = mapped_scales
            else:
                filters['enterprise_scales'] = [query_request.enterprise_scale]
        
        # 政策类型过滤
        if query_request.policy_type:
            mapped_types = []
            for policy_type, keywords in config.POLICY_TYPES.items():
                if query_request.policy_type in keywords or query_request.policy_type == policy_type:
                    mapped_types.append(policy_type)
            
            if mapped_types:
                filters['policy_types'] = mapped_types
            else:
                filters['policy_types'] = [query_request.policy_type]
        
        # 地区过滤
        if query_request.region:
            filters['regions'] = [query_request.region]
        
        logger.info(f"构建过滤条件: {filters}")
        return filters
    
    def _vector_search(self, query: str, top_k: int, filters: Dict) -> List[RetrievalResult]:
        """向量相似度搜索"""
        try:
            # 生成查询向量
            query_embedding = self.embedding_manager.encode_single_text(query)
            
            # 执行向量搜索
            results = self.vector_store.milvus.search(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters
            )
            
            # 标记来源
            for result in results:
                result.metadata['source'] = 'vector'
            
            logger.info(f"向量搜索返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []
    
    def _keyword_search(self, queries: List[str], top_k: int, filters: Dict) -> List[RetrievalResult]:
        """关键词搜索"""
        try:
            all_results = []
            
            # 对每个扩展查询执行搜索
            for query in queries[:3]:  # 限制查询数量
                results = self.vector_store.elasticsearch.search(
                    query=query,
                    filters=filters,
                    top_k=top_k // len(queries) + 5
                )
                
                # 标记来源
                for result in results:
                    result.metadata['source'] = 'keyword'
                    result.metadata['query'] = query
                
                all_results.extend(results)
            
            # 去重并按分数排序
            unique_results = self._deduplicate_results(all_results)
            unique_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"关键词搜索返回 {len(unique_results)} 个结果")
            return unique_results[:top_k]
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return []
    
    def _deduplicate_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """去重结果"""
        seen_chunks = set()
        unique_results = []
        
        for result in results:
            if result.chunk_id not in seen_chunks:
                seen_chunks.add(result.chunk_id)
                unique_results.append(result)
        
        return unique_results
    
    def _fusion_results(self, vector_results: List[RetrievalResult], 
                       keyword_results: List[RetrievalResult], 
                       top_k: int) -> List[RetrievalResult]:
        """
        融合向量搜索和关键词搜索结果
        使用Reciprocal Rank Fusion (RRF)算法
        """
        try:
            # 收集所有结果
            all_results = vector_results + keyword_results
            
            # 去重
            unique_results = self._deduplicate_results(all_results)
            
            # RRF融合
            rrf_scores = defaultdict(float)
            k = 60  # RRF参数
            
            # 向量搜索结果排名
            for rank, result in enumerate(vector_results):
                rrf_scores[result.chunk_id] += 1.0 / (k + rank + 1)
            
            # 关键词搜索结果排名
            for rank, result in enumerate(keyword_results):
                rrf_scores[result.chunk_id] += 1.0 / (k + rank + 1)
            
            # 重新计算分数
            for result in unique_results:
                original_score = result.score
                rrf_score = rrf_scores[result.chunk_id]
                
                # 融合分数：RRF + 原始分数的加权平均
                result.score = 0.6 * rrf_score + 0.4 * original_score
                result.metadata['original_score'] = original_score
                result.metadata['rrf_score'] = rrf_score
            
            # 按融合分数排序
            unique_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"融合结果: {len(unique_results)} 个结果")
            return unique_results[:top_k]
            
        except Exception as e:
            logger.error(f"结果融合失败: {e}")
            # 如果融合失败，返回向量搜索结果
            return vector_results[:top_k]
    
    def _post_process_results(self, results: List[RetrievalResult], 
                            query_request: QueryRequest) -> List[RetrievalResult]:
        """后处理结果"""
        try:
            # 企业规模匹配度检查
            if query_request.enterprise_scale or self._detect_enterprise_scale(query_request.query):
                results = self._filter_by_enterprise_scale(results, query_request.query)
            
            # 按政策匹配度重排
            results = self._rerank_by_policy_relevance(results, query_request.query)
            
            return results
            
        except Exception as e:
            logger.error(f"后处理失败: {e}")
            return results
    
    def _detect_enterprise_scale(self, query: str) -> Optional[str]:
        """从查询中检测企业规模"""
        query_lower = query.lower()
        
        for scale, keywords in config.ENTERPRISE_SCALES.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return scale
        
        return None
    
    def _filter_by_enterprise_scale(self, results: List[RetrievalResult], 
                                  query: str) -> List[RetrievalResult]:
        """根据企业规模过滤结果"""
        detected_scale = self._detect_enterprise_scale(query)
        if not detected_scale:
            return results
        
        filtered_results = []
        
        for result in results:
            content_lower = result.content.lower()
            
            # 如果是初创企业，过滤掉对大企业的要求
            if detected_scale == "初创企业":
                # 检查是否有排除性条件
                exclude_patterns = [
                    r'注册.{0,10}[三四五六七八九十]年以上',
                    r'营业收入.{0,20}千万|亿',
                    r'年销售收入.{0,20}千万|亿',
                    r'规模以上企业',
                    r'大型企业',
                    r'上市公司'
                ]
                
                should_exclude = False
                for pattern in exclude_patterns:
                    if re.search(pattern, content_lower):
                        should_exclude = True
                        break
                
                if not should_exclude:
                    filtered_results.append(result)
            else:
                filtered_results.append(result)
        
        logger.info(f"企业规模过滤: {len(results)} -> {len(filtered_results)}")
        return filtered_results
    
    def _rerank_by_policy_relevance(self, results: List[RetrievalResult], 
                                  query: str) -> List[RetrievalResult]:
        """根据政策相关性重排"""
        try:
            # 检测查询中的政策类型偏好
            policy_preferences = self._detect_policy_preferences(query)
            
            for result in results:
                relevance_boost = 0.0
                
                # 根据政策类型调整分数
                for policy_type, boost in policy_preferences.items():
                    type_keywords = config.POLICY_TYPES.get(policy_type, [])
                    for keyword in type_keywords:
                        if keyword in result.content.lower():
                            relevance_boost += boost
                            break
                
                # 应用加权
                result.score = result.score * (1.0 + relevance_boost)
                result.metadata['relevance_boost'] = relevance_boost
            
            # 重新排序
            results.sort(key=lambda x: x.score, reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"政策相关性重排失败: {e}")
            return results
    
    def _detect_policy_preferences(self, query: str) -> Dict[str, float]:
        """检测查询中的政策类型偏好"""
        preferences = {}
        query_lower = query.lower()
        
        # 资金相关关键词
        if any(keyword in query_lower for keyword in ['资金', '补贴', '奖励', '支持', '资助']):
            preferences['资金支持'] = 0.3
        
        # 税收相关关键词
        if any(keyword in query_lower for keyword in ['税收', '减税', '免税', '优惠']):
            preferences['税收优惠'] = 0.2
        
        # 人才相关关键词
        if any(keyword in query_lower for keyword in ['人才', '团队', '专家', '引进']):
            preferences['人才政策'] = 0.2
        
        # 创新相关关键词
        if any(keyword in query_lower for keyword in ['创新', '研发', '技术', '专利']):
            preferences['创新支持'] = 0.25
        
        return preferences

# 延迟创建全局检索引擎实例
_retriever = None

def get_retriever():
    """获取检索引擎实例"""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever

# 为了向后兼容，提供retriever属性
def __getattr__(name):
    if name == 'retriever':
        return get_retriever()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 