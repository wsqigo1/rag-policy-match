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
        self._query_processor = None
    
    @property
    def embedding_manager(self):
        """延迟加载embedding_manager"""
        if self._embedding_manager is None:
            from embeddings import get_embedding_manager
            self._embedding_manager = get_embedding_manager()
        return self._embedding_manager
    
    @property
    def vector_store(self):
        """延迟加载vector_store"""
        if self._vector_store is None:
            from vector_store import vector_store
            self._vector_store = vector_store
        return self._vector_store
    
    @property
    def query_processor(self):
        """延迟加载query_processor"""
        if self._query_processor is None:
            from query_understanding import get_query_processor
            self._query_processor = get_query_processor()
        return self._query_processor
    
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
            # 1. 智能查询理解
            query_understanding = self.query_processor.process_query(query_request.query)
            logger.info(f"查询理解: {query_understanding.natural_language_context}")
            
            # 2. 合并过滤条件（智能理解 + 显式请求）
            merged_filters = self._merge_filters(query_understanding.filters, query_request)
            
            # 3. 生成优化的查询集合
            optimized_queries = self._generate_optimized_queries(query_understanding)
            
            # 4. 向量检索
            vector_results = self._enhanced_vector_search(
                optimized_queries, query_request.top_k * 2, merged_filters
            )
            
            # 5. 关键词检索
            keyword_results = self._enhanced_keyword_search(
                optimized_queries, query_request.top_k * 2, merged_filters
            )
            
            # 6. 智能融合结果
            final_results = self._intelligent_fusion(
                vector_results, keyword_results, query_understanding, query_request.top_k
            )
            
            # 7. 智能后处理
            processed_results = self._intelligent_post_process(
                final_results, query_understanding, query_request
            )
            
            logger.info(f"检索完成，返回 {len(processed_results)} 个结果")
            return processed_results
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []
    
    def _merge_filters(self, smart_filters: Dict[str, Any], 
                      query_request: QueryRequest) -> Dict[str, Any]:
        """合并智能过滤和显式过滤条件"""
        merged = smart_filters.copy()
        
        # 显式请求的过滤条件优先级更高
        if query_request.industry:
            merged['industries'] = [query_request.industry]
        
        if query_request.enterprise_scale:
            merged['enterprise_scales'] = [query_request.enterprise_scale]
        
        if query_request.policy_type:
            merged['policy_types'] = [query_request.policy_type]
        
        if query_request.region:
            merged['regions'] = [query_request.region]
        
        logger.info(f"合并过滤条件: {merged}")
        return merged
    
    def _generate_optimized_queries(self, query_understanding) -> List[str]:
        """生成优化的查询集合"""
        queries = [query_understanding.processed_query]
        
        # 基于意图生成额外查询
        intent_type = query_understanding.primary_intent.intent_type
        
        if intent_type == 'check_eligibility':
            # 适用性查询增强
            queries.extend([
                "申请条件 服务对象",
                "适用范围 企业要求", 
                "准入门槛"
            ])
        elif intent_type == 'get_funding':
            # 资金支持查询增强
            queries.extend([
                "资金支持 补贴奖励",
                "专项资金 财政支持",
                "扶持资金"
            ])
        elif intent_type == 'find_policy':
            # 通用政策查找增强
            if query_understanding.entities.industries:
                for industry in query_understanding.entities.industries:
                    queries.append(f"{industry} 政策支持")
            
            if query_understanding.entities.enterprise_scales:
                for scale in query_understanding.entities.enterprise_scales:
                    queries.append(f"{scale} 扶持政策")
        
        # 使用embedding_manager的查询扩展
        expanded_queries = self.embedding_manager.expand_query(query_understanding.original_query)
        queries.extend(expanded_queries[:5])  # 限制数量
        
        # 去重并返回
        unique_queries = []
        for q in queries:
            if q not in unique_queries and len(q.strip()) > 0:
                unique_queries.append(q)
        
        logger.info(f"生成优化查询: {len(unique_queries)} 个")
        return unique_queries[:8]  # 限制总数量
    
    def _enhanced_vector_search(self, queries: List[str], top_k: int, 
                              filters: Dict) -> List[RetrievalResult]:
        """增强向量搜索"""
        try:
            all_results = []
            
            for i, query in enumerate(queries):
                # 为不同查询分配不同权重
                weight = 1.0 - (i * 0.1)  # 前面的查询权重更高
                
                query_embedding = self.embedding_manager.encode_single_text(query)
                
                results = self.vector_store.milvus.search(
                    query_embedding=query_embedding,
                    top_k=min(top_k // len(queries) + 10, 20),
                    filters=filters
                )
                
                # 应用查询权重
                for result in results:
                    result.score *= weight
                    result.metadata['source'] = 'vector'
                    result.metadata['query'] = query
                    result.metadata['query_weight'] = weight
                
                all_results.extend(results)
            
            # 去重并排序
            unique_results = self._deduplicate_results(all_results)
            unique_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"增强向量搜索返回 {len(unique_results)} 个结果")
            return unique_results[:top_k]
            
        except Exception as e:
            logger.error(f"增强向量搜索失败: {e}")
            return []
    
    def _enhanced_keyword_search(self, queries: List[str], top_k: int, 
                               filters: Dict) -> List[RetrievalResult]:
        """增强关键词搜索"""
        try:
            all_results = []
            
            for i, query in enumerate(queries):
                weight = 1.0 - (i * 0.1)
                
                results = self.vector_store.elasticsearch.search(
                    query=query,
                    filters=filters,
                    top_k=min(top_k // len(queries) + 5, 15)
                )
                
                # 应用查询权重
                for result in results:
                    result.score *= weight
                    result.metadata['source'] = 'keyword'
                    result.metadata['query'] = query
                    result.metadata['query_weight'] = weight
                
                all_results.extend(results)
            
            # 去重并排序
            unique_results = self._deduplicate_results(all_results)
            unique_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"增强关键词搜索返回 {len(unique_results)} 个结果")
            return unique_results[:top_k]
            
        except Exception as e:
            logger.error(f"增强关键词搜索失败: {e}")
            return []
    
    def _intelligent_fusion(self, vector_results: List[RetrievalResult], 
                          keyword_results: List[RetrievalResult],
                          query_understanding, top_k: int) -> List[RetrievalResult]:
        """智能融合结果"""
        try:
            # 根据查询复杂度调整融合策略
            complexity = query_understanding.query_complexity
            
            if complexity == 'simple':
                # 简单查询：更依赖向量搜索
                vector_weight = 0.7
                keyword_weight = 0.3
            elif complexity == 'moderate':
                # 中等查询：平衡权重
                vector_weight = 0.6
                keyword_weight = 0.4
            else:
                # 复杂查询：更依赖关键词搜索
                vector_weight = 0.5
                keyword_weight = 0.5
            
            # 收集所有结果
            all_results = vector_results + keyword_results
            unique_results = self._deduplicate_results(all_results)
            
            # 智能RRF融合
            rrf_scores = defaultdict(float)
            k = 60
            
            # 向量搜索结果排名（应用复杂度权重）
            for rank, result in enumerate(vector_results):
                rrf_scores[result.chunk_id] += vector_weight / (k + rank + 1)
            
            # 关键词搜索结果排名（应用复杂度权重）
            for rank, result in enumerate(keyword_results):
                rrf_scores[result.chunk_id] += keyword_weight / (k + rank + 1)
            
            # 重新计算分数
            for result in unique_results:
                original_score = result.score
                rrf_score = rrf_scores[result.chunk_id]
                
                # 基于意图的额外加权
                intent_boost = self._calculate_intent_boost(
                    result, query_understanding.primary_intent
                )
                
                # 融合分数
                result.score = 0.5 * rrf_score + 0.3 * original_score + 0.2 * intent_boost
                result.metadata['original_score'] = original_score
                result.metadata['rrf_score'] = rrf_score
                result.metadata['intent_boost'] = intent_boost
            
            # 按融合分数排序
            unique_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"智能融合结果: {len(unique_results)} 个结果")
            return unique_results[:top_k]
            
        except Exception as e:
            logger.error(f"智能融合失败: {e}")
            return vector_results[:top_k]
    
    def _calculate_intent_boost(self, result: RetrievalResult, 
                              primary_intent) -> float:
        """计算基于意图的分数提升"""
        content_lower = result.content.lower()
        intent_type = primary_intent.intent_type
        boost = 0.0
        
        if intent_type == 'check_eligibility':
            # 查找适用性相关内容
            if any(word in content_lower for word in ['适用', '服务对象', '申请条件', '适用范围']):
                boost += 0.3
            if any(word in content_lower for word in ['门槛', '要求', '条件']):
                boost += 0.2
        
        elif intent_type == 'get_funding':
            # 查找资金支持相关内容
            if any(word in content_lower for word in ['资金', '补贴', '奖励', '资助']):
                boost += 0.3
            if any(word in content_lower for word in ['万元', '支持金额', '最高']):
                boost += 0.2
        
        elif intent_type == 'get_requirements':
            # 查找申请要求相关内容
            if any(word in content_lower for word in ['申请', '申报', '材料', '流程']):
                boost += 0.3
        
        return min(boost, 0.5)  # 限制最大提升
    
    def _intelligent_post_process(self, results: List[RetrievalResult],
                                query_understanding, query_request: QueryRequest) -> List[RetrievalResult]:
        """智能后处理"""
        try:
            # 企业规模智能过滤
            if query_understanding.entities.enterprise_scales:
                results = self._smart_enterprise_scale_filter(
                    results, query_understanding.entities.enterprise_scales[0]
                )
            elif self._detect_enterprise_scale(query_understanding.original_query):
                detected_scale = self._detect_enterprise_scale(query_understanding.original_query)
                results = self._smart_enterprise_scale_filter(results, detected_scale)
            
            # 行业相关性提升
            if query_understanding.entities.industries:
                results = self._boost_industry_relevance(
                    results, query_understanding.entities.industries
                )
            
            # 政策适用性智能排序
            results = self._smart_applicability_ranking(results, query_understanding)
            
            return results
            
        except Exception as e:
            logger.error(f"智能后处理失败: {e}")
            return results
    
    def _smart_enterprise_scale_filter(self, results: List[RetrievalResult], 
                                     target_scale: str) -> List[RetrievalResult]:
        """智能企业规模过滤"""
        if target_scale != "初创企业":
            return results
        
        # 对初创企业进行特殊过滤
        filtered_results = []
        exclude_score_penalty = 0.3
        
        for result in results:
            content_lower = result.content.lower()
            should_exclude = False
            
            # 强排除条件
            strong_exclude_patterns = [
                r'注册.{0,10}[三四五六七八九十]年以上',
                r'成立.{0,10}[三四五六七八九十]年以上',
                r'营业收入.{0,20}[千万亿]',
                r'年销售收入.{0,20}[千万亿]',
                r'上市公司',
                r'规模以上企业'
            ]
            
            for pattern in strong_exclude_patterns:
                if re.search(pattern, content_lower):
                    should_exclude = True
                    break
            
            if not should_exclude:
                # 软排除条件（降低分数但不完全排除）
                soft_exclude_patterns = [
                    r'大型企业', r'中型企业', r'成熟企业'
                ]
                
                for pattern in soft_exclude_patterns:
                    if re.search(pattern, content_lower):
                        result.score *= (1 - exclude_score_penalty)
                        result.metadata['scale_penalty'] = exclude_score_penalty
                        break
                
                # 初创企业友好内容加分
                startup_friendly_patterns = [
                    r'初创|创业|新成立|起步',
                    r'孵化|众创|创新创业',
                    r'低门槛|无需|不限'
                ]
                
                for pattern in startup_friendly_patterns:
                    if re.search(pattern, content_lower):
                        result.score *= 1.2
                        result.metadata['startup_boost'] = 0.2
                        break
                
                filtered_results.append(result)
        
        logger.info(f"初创企业规模过滤: {len(results)} -> {len(filtered_results)}")
        return filtered_results
    
    def _boost_industry_relevance(self, results: List[RetrievalResult], 
                                industries: List[str]) -> List[RetrievalResult]:
        """提升行业相关性"""
        industry_keywords = []
        for industry in industries:
            industry_keywords.extend(config.INDUSTRY_MAPPING.get(industry, []))
        
        for result in results:
            content_lower = result.content.lower()
            relevance_boost = 0.0
            
            for keyword in industry_keywords:
                if keyword in content_lower:
                    relevance_boost += 0.1
            
            if relevance_boost > 0:
                result.score *= (1 + min(relevance_boost, 0.3))
                result.metadata['industry_boost'] = relevance_boost
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def _smart_applicability_ranking(self, results: List[RetrievalResult],
                                   query_understanding) -> List[RetrievalResult]:
        """智能适用性排序"""
        intent_type = query_understanding.primary_intent.intent_type
        
        if intent_type == 'check_eligibility':
            # 优先显示包含明确适用条件的内容
            for result in results:
                content_lower = result.content.lower()
                if any(word in content_lower for word in ['服务对象', '适用范围', '申请条件']):
                    result.score *= 1.15
                    result.metadata['eligibility_boost'] = 0.15
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    # 保持现有的辅助方法
    def _deduplicate_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """去重结果"""
        seen_chunks = set()
        unique_results = []
        
        for result in results:
            if result.chunk_id not in seen_chunks:
                seen_chunks.add(result.chunk_id)
                unique_results.append(result)
        
        return unique_results
    
    def _detect_enterprise_scale(self, query: str) -> Optional[str]:
        """从查询中检测企业规模"""
        query_lower = query.lower()
        
        for scale, keywords in config.ENTERPRISE_SCALES.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return scale
        
        return None

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