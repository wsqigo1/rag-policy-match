import logging
import numpy as np
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
from collections import defaultdict

from config import config
from models import RetrievalResult, QueryRequest, PolicyChunk

logger = logging.getLogger(__name__)

class RetrievalStrategy(Enum):
    """检索策略枚举"""
    SIMPLE = "simple"                    # 简单检索
    HYBRID = "hybrid"                    # 混合检索
    HIERARCHICAL = "hierarchical"       # 层次化检索
    MULTI_REPRESENTATION = "multi_rep"  # 多表示检索
    FULL_ADVANCED = "full_advanced"     # 全高级功能

@dataclass
class AdvancedQueryRequest:
    """高级查询请求"""
    query: str
    strategy: RetrievalStrategy = RetrievalStrategy.FULL_ADVANCED
    use_llm_enhancement: bool = True
    use_reranking: bool = True
    use_hierarchical_index: bool = True
    use_query_understanding: bool = True
    company_context: Optional[Dict] = None
    top_k: int = 10
    metadata: Optional[Dict] = None

@dataclass
class AdvancedRetrievalResponse:
    """高级检索响应"""
    results: List[RetrievalResult]
    llm_generated_summary: Optional[str] = None
    optimization_strategy: Optional[str] = None
    query_understanding: Optional[Dict] = None
    retrieval_stats: Optional[Dict] = None
    success: bool = True
    error: Optional[str] = None

class AdvancedRetriever:
    """高级检索器 - 集成所有优化功能"""
    
    def __init__(self):
        # 延迟加载所有组件
        self._embedding_manager = None
        self._vector_store = None
        self._llm_manager = None
        self._hierarchical_index = None
        self._reranker = None
        self._query_processor = None
        
        # 检索统计
        self.stats = defaultdict(int)
    
    @property
    def embedding_manager(self):
        """延迟加载embedding管理器"""
        if self._embedding_manager is None:
            from embeddings import get_embedding_manager
            self._embedding_manager = get_embedding_manager()
        return self._embedding_manager
    
    @property
    def vector_store(self):
        """延迟加载向量存储"""
        if self._vector_store is None:
            from vector_store import get_vector_store
            self._vector_store = get_vector_store()
        return self._vector_store
    
    @property
    def llm_manager(self):
        """延迟加载LLM管理器"""
        if self._llm_manager is None:
            from llm_manager import get_llm_manager
            self._llm_manager = get_llm_manager()
        return self._llm_manager
    
    @property
    def hierarchical_index(self):
        """延迟加载层次索引"""
        if self._hierarchical_index is None:
            from multi_representation_index import get_hierarchical_index_manager
            self._hierarchical_index = get_hierarchical_index_manager()
        return self._hierarchical_index
    
    @property
    def reranker(self):
        """延迟加载重排器"""
        if self._reranker is None:
            from reranker import get_advanced_reranker
            self._reranker = get_advanced_reranker()
        return self._reranker
    
    @property
    def query_processor(self):
        """延迟加载查询处理器"""
        if self._query_processor is None:
            from query_understanding import get_query_processor
            self._query_processor = get_query_processor()
        return self._query_processor
    
    async def retrieve(self, request: AdvancedQueryRequest) -> AdvancedRetrievalResponse:
        """高级检索主方法"""
        try:
            logger.info(f"开始高级检索: {request.query} (策略: {request.strategy.value})")
            
            # 1. 查询理解和增强
            query_understanding = None
            if request.use_query_understanding:
                query_understanding = await self._enhance_query_understanding(request.query)
            
            # 2. 多策略检索
            raw_results = await self._multi_strategy_retrieval(request, query_understanding)
            
            # 3. 高级重排
            reranked_results = []
            if request.use_reranking and raw_results:
                reranked_results = await self._advanced_reranking(
                    request.query, raw_results, query_understanding, request.top_k
                )
            else:
                reranked_results = raw_results[:request.top_k]
            
            # 4. LLM增强生成
            llm_summary = None
            optimization_strategy = None
            if request.use_llm_enhancement and reranked_results:
                llm_summary, optimization_strategy = await self._llm_enhancement(
                    request, reranked_results, query_understanding
                )
            
            # 5. 统计信息
            retrieval_stats = self._generate_stats(request, raw_results, reranked_results)
            
            return AdvancedRetrievalResponse(
                results=reranked_results,
                llm_generated_summary=llm_summary,
                optimization_strategy=optimization_strategy,
                query_understanding=query_understanding,
                retrieval_stats=retrieval_stats,
                success=True
            )
            
        except Exception as e:
            logger.error(f"高级检索失败: {e}")
            return AdvancedRetrievalResponse(
                results=[],
                success=False,
                error=str(e)
            )
    
    async def _enhance_query_understanding(self, query: str) -> Dict[str, Any]:
        """增强查询理解"""
        try:
            # 1. 基础查询理解
            basic_understanding = self.query_processor.process_query(query)
            
            # 2. LLM增强理解（如果可用）
            llm_understanding = None
            if config.DYNAMIC_PROMPT_OPTIMIZATION:
                response = self.llm_manager.understand_query(query)
                if response.success:
                    llm_understanding = self._parse_llm_understanding(response.content)
            
            # 3. 合并理解结果
            enhanced_understanding = {
                "original_query": query,
                "basic_understanding": {
                    "intent": basic_understanding.primary_intent.intent_type,
                    "entities": {
                        "industries": basic_understanding.entities.industries,
                        "enterprise_scales": basic_understanding.entities.enterprise_scales,
                        "policy_types": basic_understanding.entities.policy_types
                    },
                    "complexity": basic_understanding.query_complexity,
                    "filters": basic_understanding.filters
                },
                "llm_understanding": llm_understanding,
                "optimized_queries": self._generate_optimized_queries(basic_understanding, llm_understanding)
            }
            
            return enhanced_understanding
            
        except Exception as e:
            logger.error(f"查询理解增强失败: {e}")
            return {"original_query": query, "error": str(e)}
    
    async def _multi_strategy_retrieval(self, request: AdvancedQueryRequest, 
                                      query_understanding: Optional[Dict]) -> List[RetrievalResult]:
        """多策略检索"""
        all_results = []
        
        try:
            # 策略1: 传统混合检索
            if request.strategy in [RetrievalStrategy.HYBRID, RetrievalStrategy.FULL_ADVANCED]:
                hybrid_results = await self._hybrid_retrieval(request, query_understanding)
                all_results.extend(hybrid_results)
            
            # 策略2: 层次化检索
            if request.use_hierarchical_index and request.strategy in [
                RetrievalStrategy.HIERARCHICAL, RetrievalStrategy.MULTI_REPRESENTATION, RetrievalStrategy.FULL_ADVANCED
            ]:
                hierarchical_results = await self._hierarchical_retrieval(request, query_understanding)
                all_results.extend(hierarchical_results)
            
            # 策略3: 多表示检索
            if request.strategy in [RetrievalStrategy.MULTI_REPRESENTATION, RetrievalStrategy.FULL_ADVANCED]:
                multi_rep_results = await self._multi_representation_retrieval(request, query_understanding)
                all_results.extend(multi_rep_results)
            
            # 去重并初步排序
            unique_results = self._deduplicate_and_merge(all_results)
            
            logger.info(f"多策略检索完成，获得 {len(unique_results)} 个唯一结果")
            return unique_results
            
        except Exception as e:
            logger.error(f"多策略检索失败: {e}")
            return []
    
    async def _hybrid_retrieval(self, request: AdvancedQueryRequest, 
                              query_understanding: Optional[Dict]) -> List[RetrievalResult]:
        """传统混合检索"""
        try:
            # 使用现有的混合检索器
            from retriever import get_retriever
            retriever = get_retriever()
            
            # 构建查询请求
            query_request = QueryRequest(
                query=request.query,
                top_k=min(request.top_k * 3, 100),  # 获取更多候选
                industry=query_understanding.get("basic_understanding", {}).get("entities", {}).get("industries", [None])[0] if query_understanding else None,
                enterprise_scale=query_understanding.get("basic_understanding", {}).get("entities", {}).get("enterprise_scales", [None])[0] if query_understanding else None
            )
            
            results = retriever.retrieve(query_request)
            
            # 添加来源标记
            for result in results:
                result.metadata['retrieval_source'] = 'hybrid'
            
            return results
            
        except Exception as e:
            logger.error(f"混合检索失败: {e}")
            return []
    
    async def _hierarchical_retrieval(self, request: AdvancedQueryRequest, 
                                    query_understanding: Optional[Dict]) -> List[RetrievalResult]:
        """层次化检索"""
        try:
            # 动态调整层次权重
            level_weights = self._calculate_dynamic_level_weights(query_understanding)
            
            results = self.hierarchical_index.hierarchical_search(
                query=request.query,
                top_k=min(request.top_k * 2, 50),
                level_weights=level_weights
            )
            
            # 添加来源标记
            for result in results:
                result.metadata['retrieval_source'] = 'hierarchical'
            
            return results
            
        except Exception as e:
            logger.error(f"层次化检索失败: {e}")
            return []
    
    async def _multi_representation_retrieval(self, request: AdvancedQueryRequest, 
                                            query_understanding: Optional[Dict]) -> List[RetrievalResult]:
        """多表示检索"""
        try:
            results = []
            
            # 稠密向量检索
            dense_results = await self._dense_vector_search(request.query, request.top_k)
            results.extend(dense_results)
            
            # 稀疏向量检索 (BM25/TF-IDF)
            sparse_results = await self._sparse_vector_search(request.query, request.top_k)
            results.extend(sparse_results)
            
            # 关键词增强检索
            keyword_results = await self._keyword_enhanced_search(request.query, query_understanding, request.top_k)
            results.extend(keyword_results)
            
            # 添加来源标记
            for result in results:
                result.metadata['retrieval_source'] = 'multi_representation'
            
            return results
            
        except Exception as e:
            logger.error(f"多表示检索失败: {e}")
            return []
    
    async def _advanced_reranking(self, query: str, candidates: List[RetrievalResult], 
                                query_understanding: Optional[Dict], top_k: int) -> List[RetrievalResult]:
        """高级重排"""
        try:
            from reranker import RerankRequest, RerankerType
            
            # 自动选择重排策略
            reranker_type = self.reranker.auto_select_reranker(
                candidates, 
                query_understanding.get("basic_understanding", {}).get("complexity", "moderate") if query_understanding else "moderate"
            )
            
            # 构建重排请求
            rerank_request = RerankRequest(
                query=query,
                candidates=candidates,
                reranker_type=reranker_type,
                top_k=top_k,
                context=query_understanding
            )
            
            # 执行重排
            rerank_result = self.reranker.rerank(rerank_request)
            
            if rerank_result.success:
                logger.info(f"重排完成，使用方法: {rerank_result.method_used}")
                return rerank_result.reranked_results
            else:
                logger.warning(f"重排失败: {rerank_result.error}")
                return candidates[:top_k]
                
        except Exception as e:
            logger.error(f"高级重排失败: {e}")
            return candidates[:top_k]
    
    async def _llm_enhancement(self, request: AdvancedQueryRequest, 
                             results: List[RetrievalResult],
                             query_understanding: Optional[Dict]) -> Tuple[Optional[str], Optional[str]]:
        """LLM增强生成"""
        try:
            # 1. 生成政策匹配摘要
            summary = None
            if results:
                policies_data = [
                    {
                        'title': f"政策{i+1}",
                        'content': result.content[:300],
                        'policy_id': result.policy_id
                    }
                    for i, result in enumerate(results[:5])  # 只用前5个结果
                ]
                
                response = self.llm_manager.match_policies(
                    user_query=request.query,
                    retrieved_policies=policies_data,
                    company_context=request.company_context
                )
                
                if response.success:
                    summary = response.content
            
            # 2. 生成优化策略
            optimization_strategy = None
            if request.company_context and results:
                strategy_response = self.llm_manager.generate_optimization_strategy(
                    company_status=request.company_context,
                    analysis_results=query_understanding or {},
                    target_policies=policies_data[:3] if 'policies_data' in locals() else []
                )
                
                if strategy_response.success:
                    optimization_strategy = strategy_response.content
            
            return summary, optimization_strategy
            
        except Exception as e:
            logger.error(f"LLM增强失败: {e}")
            return None, None
    
    def _parse_llm_understanding(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM理解结果"""
        try:
            # 简化的解析逻辑
            parsed = {}
            
            # 提取主要意图
            intent_match = re.search(r'\*\*主要意图：\*\*\s*([^\n]+)', llm_response)
            if intent_match:
                parsed['intent'] = intent_match.group(1).strip()
            
            # 提取复杂度
            complexity_match = re.search(r'\*\*查询复杂度：\*\*\s*([^\n]+)', llm_response)
            if complexity_match:
                parsed['complexity'] = complexity_match.group(1).strip()
            
            # 提取优化查询
            query_match = re.search(r'\*\*优化查询：\*\*\s*([^\n]+)', llm_response)
            if query_match:
                parsed['optimized_query'] = query_match.group(1).strip()
            
            return parsed
            
        except Exception as e:
            logger.error(f"解析LLM理解失败: {e}")
            return {}
    
    def _generate_optimized_queries(self, basic_understanding, llm_understanding: Optional[Dict]) -> List[str]:
        """生成优化查询"""
        queries = [basic_understanding.processed_query]
        
        # 基于基础理解的查询扩展
        queries.extend(self.embedding_manager.expand_query(basic_understanding.original_query)[:3])
        
        # 基于LLM理解的查询
        if llm_understanding and 'optimized_query' in llm_understanding:
            queries.append(llm_understanding['optimized_query'])
        
        return list(set(queries))  # 去重
    
    def _calculate_dynamic_level_weights(self, query_understanding: Optional[Dict]) -> Dict:
        """动态计算层次权重"""
        from multi_representation_index import IndexLevel
        
        default_weights = {
            IndexLevel.POLICY: 1.0,
            IndexLevel.SECTION: 0.8,
            IndexLevel.SENTENCE: 0.6
        }
        
        if not query_understanding:
            return default_weights
        
        # 根据查询意图调整权重
        intent = query_understanding.get("basic_understanding", {}).get("intent", "")
        
        if intent == "check_eligibility":
            # 适用性查询更关注详细条件
            return {
                IndexLevel.POLICY: 0.7,
                IndexLevel.SECTION: 1.0,
                IndexLevel.SENTENCE: 0.9
            }
        elif intent == "get_funding":
            # 资金查询更关注政策概览
            return {
                IndexLevel.POLICY: 1.0,
                IndexLevel.SECTION: 0.9,
                IndexLevel.SENTENCE: 0.6
            }
        
        return default_weights
    
    async def _dense_vector_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """稠密向量搜索"""
        try:
            query_embedding = self.embedding_manager.encode_single_text(query)
            results = self.vector_store.milvus.search(
                query_embedding=query_embedding,
                top_k=top_k
            )
            
            for result in results:
                result.metadata['search_type'] = 'dense_vector'
            
            return results
            
        except Exception as e:
            logger.error(f"稠密向量搜索失败: {e}")
            return []
    
    async def _sparse_vector_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """稀疏向量搜索"""
        try:
            # 这里可以集成BM25等稀疏搜索
            results = self.vector_store.elasticsearch.search(
                query=query,
                top_k=top_k
            )
            
            for result in results:
                result.metadata['search_type'] = 'sparse_vector'
            
            return results
            
        except Exception as e:
            logger.error(f"稀疏向量搜索失败: {e}")
            return []
    
    async def _keyword_enhanced_search(self, query: str, query_understanding: Optional[Dict], top_k: int) -> List[RetrievalResult]:
        """关键词增强搜索"""
        try:
            # 提取关键词并进行增强搜索
            keywords = []
            if query_understanding:
                entities = query_understanding.get("basic_understanding", {}).get("entities", {})
                keywords.extend(entities.get("industries", []))
                keywords.extend(entities.get("policy_types", []))
            
            # 使用关键词进行搜索
            enhanced_query = f"{query} {' '.join(keywords)}"
            results = self.vector_store.elasticsearch.search(
                query=enhanced_query,
                top_k=top_k
            )
            
            for result in results:
                result.metadata['search_type'] = 'keyword_enhanced'
            
            return results
            
        except Exception as e:
            logger.error(f"关键词增强搜索失败: {e}")
            return []
    
    def _deduplicate_and_merge(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """去重并合并结果"""
        seen_chunks = {}
        merged_results = []
        
        for result in results:
            if result.chunk_id in seen_chunks:
                # 合并分数（取最高分）
                existing = seen_chunks[result.chunk_id]
                if result.score > existing.score:
                    existing.score = result.score
                    # 合并元数据
                    sources = existing.metadata.get('retrieval_sources', [])
                    sources.append(result.metadata.get('retrieval_source', 'unknown'))
                    existing.metadata['retrieval_sources'] = list(set(sources))
            else:
                result.metadata['retrieval_sources'] = [result.metadata.get('retrieval_source', 'unknown')]
                seen_chunks[result.chunk_id] = result
                merged_results.append(result)
        
        # 按分数排序
        merged_results.sort(key=lambda x: x.score, reverse=True)
        return merged_results
    
    def _generate_stats(self, request: AdvancedQueryRequest, 
                       raw_results: List[RetrievalResult],
                       final_results: List[RetrievalResult]) -> Dict[str, Any]:
        """生成检索统计"""
        return {
            "strategy_used": request.strategy.value,
            "raw_results_count": len(raw_results),
            "final_results_count": len(final_results),
            "used_llm_enhancement": request.use_llm_enhancement,
            "used_reranking": request.use_reranking,
            "used_hierarchical_index": request.use_hierarchical_index,
            "retrieval_sources": list(set([
                source for result in final_results 
                for source in result.metadata.get('retrieval_sources', [])
            ])),
            "avg_score": sum(r.score for r in final_results) / len(final_results) if final_results else 0
        }

# 全局高级检索器实例
_advanced_retriever = None

def get_advanced_retriever() -> AdvancedRetriever:
    """获取高级检索器实例"""
    global _advanced_retriever
    if _advanced_retriever is None:
        _advanced_retriever = AdvancedRetriever()
    return _advanced_retriever 