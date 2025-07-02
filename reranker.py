import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from collections import defaultdict

from config import config
from models import RetrievalResult

logger = logging.getLogger(__name__)

class RerankerType(Enum):
    """重排器类型枚举"""
    CROSS_ENCODER = "cross_encoder"     # 跨编码器重排
    LLM_RERANK = "llm_rerank"          # LLM重排
    RULE_BASED = "rule_based"          # 规则重排
    MULTI_STAGE = "multi_stage"        # 多阶段重排

@dataclass
class RerankRequest:
    """重排请求"""
    query: str
    candidates: List[RetrievalResult]
    reranker_type: RerankerType = RerankerType.MULTI_STAGE
    top_k: int = 10
    context: Optional[Dict[str, Any]] = None

@dataclass
class RerankResult:
    """重排结果"""
    reranked_results: List[RetrievalResult]
    rerank_scores: List[float]
    method_used: str
    success: bool = True
    error: Optional[str] = None

class CrossEncoderReranker:
    """跨编码器重排器"""
    
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载跨编码器模型"""
        try:
            from sentence_transformers import CrossEncoder
            # 使用中文跨编码器模型（如果有的话）
            model_names = [
                "BAAI/bge-reranker-base",
                "BAAI/bge-reranker-large", 
                "cross-encoder/ms-marco-MiniLM-L-12-v2"
            ]
            
            for model_name in model_names:
                try:
                    self.model = CrossEncoder(model_name)
                    logger.info(f"跨编码器模型加载成功: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"模型 {model_name} 加载失败: {e}")
                    continue
            
            if not self.model:
                logger.warning("所有跨编码器模型加载失败，将使用规则重排")
                
        except Exception as e:
            logger.error(f"跨编码器初始化失败: {e}")
            self.model = None
    
    def rerank(self, query: str, candidates: List[RetrievalResult], top_k: int = 10) -> RerankResult:
        """跨编码器重排"""
        if not self.model or not candidates:
            return RerankResult(
                reranked_results=candidates[:top_k],
                rerank_scores=[],
                method_used="fallback",
                success=False,
                error="跨编码器模型未加载"
            )
        
        try:
            # 准备输入对
            query_doc_pairs = []
            for candidate in candidates:
                # 限制文档长度避免模型输入过长
                content = candidate.content[:512]
                query_doc_pairs.append([query, content])
            
            # 计算相关性分数
            scores = self.model.predict(query_doc_pairs)
            
            # 结合原分数和重排分数
            combined_results = []
            for i, candidate in enumerate(candidates):
                new_score = 0.7 * float(scores[i]) + 0.3 * candidate.score
                candidate.score = new_score
                candidate.metadata['rerank_score'] = float(scores[i])
                candidate.metadata['original_score'] = candidate.score
                combined_results.append(candidate)
            
            # 排序
            combined_results.sort(key=lambda x: x.score, reverse=True)
            
            return RerankResult(
                reranked_results=combined_results[:top_k],
                rerank_scores=scores.tolist(),
                method_used="cross_encoder",
                success=True
            )
            
        except Exception as e:
            logger.error(f"跨编码器重排失败: {e}")
            return RerankResult(
                reranked_results=candidates[:top_k],
                rerank_scores=[],
                method_used="fallback",
                success=False,
                error=str(e)
            )

class LLMReranker:
    """LLM重排器"""
    
    def __init__(self):
        self._llm_manager = None
    
    @property
    def llm_manager(self):
        """延迟加载LLM管理器"""
        if self._llm_manager is None:
            from llm_manager import get_llm_manager
            self._llm_manager = get_llm_manager()
        return self._llm_manager
    
    def rerank(self, query: str, candidates: List[RetrievalResult], top_k: int = 10) -> RerankResult:
        """LLM重排"""
        if not candidates:
            return RerankResult(
                reranked_results=[],
                rerank_scores=[],
                method_used="llm_rerank",
                success=True
            )
        
        try:
            # 分批处理（避免输入过长）
            batch_size = config.LLM_RERANK_BATCH_SIZE
            all_reranked = []
            
            for i in range(0, len(candidates), batch_size):
                batch = candidates[i:i + batch_size]
                batch_result = self._rerank_batch(query, batch)
                all_reranked.extend(batch_result)
            
            # 最终排序
            all_reranked.sort(key=lambda x: x.score, reverse=True)
            
            return RerankResult(
                reranked_results=all_reranked[:top_k],
                rerank_scores=[r.score for r in all_reranked[:top_k]],
                method_used="llm_rerank",
                success=True
            )
            
        except Exception as e:
            logger.error(f"LLM重排失败: {e}")
            return RerankResult(
                reranked_results=candidates[:top_k],
                rerank_scores=[],
                method_used="fallback",
                success=False,
                error=str(e)
            )
    
    def _rerank_batch(self, query: str, batch: List[RetrievalResult]) -> List[RetrievalResult]:
        """重排一个批次"""
        try:
            # 格式化候选结果
            candidates_data = []
            for i, result in enumerate(batch):
                candidates_data.append({
                    'chunk_id': result.chunk_id,
                    'content': result.content[:300],  # 限制长度
                    'score': result.score
                })
            
            # 调用LLM重排
            response = self.llm_manager.rerank_results(query, candidates_data)
            
            if response.success:
                # 解析LLM重排结果
                reranked_results = self._parse_llm_rerank_response(response.content, batch)
                return reranked_results
            else:
                logger.warning(f"LLM重排失败: {response.error}")
                return batch
                
        except Exception as e:
            logger.error(f"批次重排失败: {e}")
            return batch
    
    def _parse_llm_rerank_response(self, response_content: str, 
                                  original_batch: List[RetrievalResult]) -> List[RetrievalResult]:
        """解析LLM重排响应"""
        try:
            # 简化的解析逻辑：查找排名模式
            lines = response_content.split('\n')
            rank_pattern = r'(\d+)\.\s*([^-\s]+)'
            
            reranked_map = {}
            for line in lines:
                match = re.search(rank_pattern, line)
                if match:
                    rank = int(match.group(1))
                    chunk_id = match.group(2).strip()
                    reranked_map[chunk_id] = rank
            
            # 根据LLM排名重新排序
            def get_llm_rank(result):
                chunk_id = result.chunk_id
                return reranked_map.get(chunk_id, 999)  # 未找到的排到最后
            
            sorted_results = sorted(original_batch, key=get_llm_rank)
            
            # 更新分数
            for i, result in enumerate(sorted_results):
                llm_rank = get_llm_rank(result)
                if llm_rank != 999:
                    # 基于排名计算新分数
                    rank_score = 1.0 / (llm_rank + 1)
                    result.score = 0.6 * rank_score + 0.4 * result.score
                    result.metadata['llm_rank'] = llm_rank
            
            return sorted_results
            
        except Exception as e:
            logger.error(f"解析LLM重排响应失败: {e}")
            return original_batch

class RuleBasedReranker:
    """基于规则的重排器"""
    
    def __init__(self):
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict[str, Any]:
        """加载重排规则"""
        return {
            # 查询-文档匹配规则
            "exact_match_boost": 1.5,          # 精确匹配加分
            "partial_match_boost": 1.2,        # 部分匹配加分
            "keyword_density_boost": 1.3,      # 关键词密度加分
            
            # 内容质量规则
            "length_preference": {             # 长度偏好
                "min_length": 50,
                "optimal_length": 200,
                "max_length": 1000,
                "short_penalty": 0.8,
                "long_penalty": 0.9
            },
            
            # 结构化信息偏好
            "structured_content_boost": 1.4,   # 结构化内容加分
            "title_match_boost": 1.6,         # 标题匹配加分
            
            # 政策特定规则
            "policy_section_preferences": {    # 政策章节偏好
                "申请条件": 1.5,
                "服务对象": 1.4,
                "支持内容": 1.3,
                "申请流程": 1.2,
                "联系方式": 1.1
            }
        }
    
    def rerank(self, query: str, candidates: List[RetrievalResult], 
              context: Optional[Dict] = None, top_k: int = 10) -> RerankResult:
        """基于规则的重排"""
        if not candidates:
            return RerankResult(
                reranked_results=[],
                rerank_scores=[],
                method_used="rule_based",
                success=True
            )
        
        try:
            # 提取查询关键词
            query_keywords = self._extract_keywords(query)
            
            # 为每个候选结果计算规则分数
            for candidate in candidates:
                rule_score = self._calculate_rule_score(
                    query, query_keywords, candidate, context
                )
                
                # 结合原分数
                combined_score = 0.7 * candidate.score + 0.3 * rule_score
                candidate.score = combined_score
                candidate.metadata['rule_score'] = rule_score
                candidate.metadata['original_score'] = candidate.score
            
            # 排序
            candidates.sort(key=lambda x: x.score, reverse=True)
            
            return RerankResult(
                reranked_results=candidates[:top_k],
                rerank_scores=[r.score for r in candidates[:top_k]],
                method_used="rule_based",
                success=True
            )
            
        except Exception as e:
            logger.error(f"规则重排失败: {e}")
            return RerankResult(
                reranked_results=candidates[:top_k],
                rerank_scores=[],
                method_used="fallback",
                success=False,
                error=str(e)
            )
    
    def _calculate_rule_score(self, query: str, query_keywords: List[str], 
                            candidate: RetrievalResult, context: Optional[Dict]) -> float:
        """计算规则分数"""
        score = 1.0
        content = candidate.content.lower()
        query_lower = query.lower()
        
        # 1. 精确匹配检查
        if query_lower in content:
            score *= self.rules["exact_match_boost"]
        
        # 2. 关键词匹配分数
        keyword_matches = sum(1 for kw in query_keywords if kw in content)
        if keyword_matches > 0:
            keyword_ratio = keyword_matches / len(query_keywords)
            score *= (1 + keyword_ratio * self.rules["partial_match_boost"])
        
        # 3. 关键词密度加分
        keyword_density = sum(content.count(kw) for kw in query_keywords) / len(content)
        if keyword_density > 0.01:  # 1%以上的关键词密度
            score *= self.rules["keyword_density_boost"]
        
        # 4. 内容长度偏好
        length_score = self._calculate_length_score(len(content))
        score *= length_score
        
        # 5. 结构化内容检查
        if self._is_structured_content(content):
            score *= self.rules["structured_content_boost"]
        
        # 6. 政策章节偏好
        section = candidate.metadata.get('section', '')
        if section in self.rules["policy_section_preferences"]:
            score *= self.rules["policy_section_preferences"][section]
        
        # 7. 标题匹配检查
        if self._has_title_match(query_keywords, content):
            score *= self.rules["title_match_boost"]
        
        return score
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取查询关键词"""
        # 简化的关键词提取
        import jieba
        keywords = list(jieba.cut(query, cut_all=False))
        # 过滤停用词和短词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        keywords = [kw for kw in keywords if len(kw) > 1 and kw not in stop_words]
        return keywords
    
    def _calculate_length_score(self, length: int) -> float:
        """计算长度分数"""
        prefs = self.rules["length_preference"]
        
        if length < prefs["min_length"]:
            return prefs["short_penalty"]
        elif length > prefs["max_length"]:
            return prefs["long_penalty"]
        elif prefs["min_length"] <= length <= prefs["optimal_length"]:
            return 1.0
        else:
            # 在最优长度和最大长度之间线性衰减
            ratio = (prefs["max_length"] - length) / (prefs["max_length"] - prefs["optimal_length"])
            return 1.0 - (1.0 - prefs["long_penalty"]) * (1 - ratio)
    
    def _is_structured_content(self, content: str) -> bool:
        """检查是否为结构化内容"""
        # 检查是否包含结构化标记
        structured_patterns = [
            r'\d+[.、]',        # 数字编号
            r'[（\(][一二三四五六七八九十\d]+[）\)]',  # 括号编号
            r'第[一二三四五六七八九十\d]+[条章节项]',   # 条款标记
            r'[一二三四五六七八九十\d]+[、.]',        # 中文编号
        ]
        
        for pattern in structured_patterns:
            if re.search(pattern, content):
                return True
        
        return False
    
    def _has_title_match(self, query_keywords: List[str], content: str) -> bool:
        """检查是否有标题匹配"""
        # 简化的标题匹配检查：查看内容开始部分
        title_part = content[:100]
        title_keywords = sum(1 for kw in query_keywords if kw in title_part)
        return title_keywords >= len(query_keywords) * 0.5

class MultiStageReranker:
    """多阶段重排器"""
    
    def __init__(self):
        self.rule_reranker = RuleBasedReranker()
        self.cross_encoder_reranker = CrossEncoderReranker()
        self.llm_reranker = LLMReranker()
    
    def rerank(self, request: RerankRequest) -> RerankResult:
        """多阶段重排主方法"""
        try:
            candidates = request.candidates.copy()
            stage_results = []
            
            # 第一阶段：规则重排（快速过滤和初步排序）
            if len(candidates) > request.top_k * 2:
                stage1_result = self.rule_reranker.rerank(
                    request.query, 
                    candidates, 
                    request.context, 
                    top_k=request.top_k * 2
                )
                candidates = stage1_result.reranked_results
                stage_results.append(("rule_based", len(candidates)))
            
            # 第二阶段：跨编码器重排（中等精度）
            if config.RERANK_ENABLED and len(candidates) > request.top_k:
                stage2_result = self.cross_encoder_reranker.rerank(
                    request.query,
                    candidates,
                    top_k=min(request.top_k * 1.5, len(candidates))
                )
                if stage2_result.success:
                    candidates = stage2_result.reranked_results
                    stage_results.append(("cross_encoder", len(candidates)))
            
            # 第三阶段：LLM重排（高精度，少量候选）
            if config.LLM_RERANK_ENABLED and len(candidates) <= 20:
                stage3_result = self.llm_reranker.rerank(
                    request.query,
                    candidates,
                    top_k=request.top_k
                )
                if stage3_result.success:
                    candidates = stage3_result.reranked_results
                    stage_results.append(("llm_rerank", len(candidates)))
            
            # 最终结果
            final_results = candidates[:request.top_k]
            
            # 添加重排元数据
            for result in final_results:
                result.metadata['rerank_stages'] = stage_results
                result.metadata['final_rerank_method'] = 'multi_stage'
            
            return RerankResult(
                reranked_results=final_results,
                rerank_scores=[r.score for r in final_results],
                method_used=f"multi_stage: {' -> '.join([s[0] for s in stage_results])}",
                success=True
            )
            
        except Exception as e:
            logger.error(f"多阶段重排失败: {e}")
            return RerankResult(
                reranked_results=request.candidates[:request.top_k],
                rerank_scores=[],
                method_used="fallback",
                success=False,
                error=str(e)
            )

class AdvancedReranker:
    """高级重排器（统一接口）"""
    
    def __init__(self):
        self.rule_reranker = RuleBasedReranker()
        self.cross_encoder_reranker = CrossEncoderReranker()
        self.llm_reranker = LLMReranker()
        self.multi_stage_reranker = MultiStageReranker()
        
        self.reranker_map = {
            RerankerType.RULE_BASED: self.rule_reranker,
            RerankerType.CROSS_ENCODER: self.cross_encoder_reranker,
            RerankerType.LLM_RERANK: self.llm_reranker,
            RerankerType.MULTI_STAGE: self.multi_stage_reranker
        }
    
    def rerank(self, request: RerankRequest) -> RerankResult:
        """统一重排接口"""
        reranker = self.reranker_map.get(request.reranker_type)
        if not reranker:
            logger.error(f"未知的重排器类型: {request.reranker_type}")
            return RerankResult(
                reranked_results=request.candidates[:request.top_k],
                rerank_scores=[],
                method_used="fallback",
                success=False,
                error=f"未知的重排器类型: {request.reranker_type}"
            )
        
        # 根据重排器类型调用相应方法
        if request.reranker_type == RerankerType.MULTI_STAGE:
            return reranker.rerank(request)
        elif request.reranker_type == RerankerType.RULE_BASED:
            return reranker.rerank(request.query, request.candidates, request.context, request.top_k)
        else:
            return reranker.rerank(request.query, request.candidates, request.top_k)
    
    def auto_select_reranker(self, candidates: List[RetrievalResult], 
                           query_complexity: str = "moderate") -> RerankerType:
        """自动选择重排器"""
        num_candidates = len(candidates)
        
        if num_candidates <= 5:
            # 候选少，直接使用LLM重排
            return RerankerType.LLM_RERANK
        elif num_candidates <= 20 and query_complexity == "complex":
            # 中等数量且查询复杂，使用多阶段
            return RerankerType.MULTI_STAGE
        elif num_candidates <= 50:
            # 适中数量，使用跨编码器
            return RerankerType.CROSS_ENCODER
        else:
            # 大量候选，使用规则重排
            return RerankerType.RULE_BASED

# 全局重排器实例
_advanced_reranker = None

def get_advanced_reranker() -> AdvancedReranker:
    """获取高级重排器实例"""
    global _advanced_reranker
    if _advanced_reranker is None:
        _advanced_reranker = AdvancedReranker()
    return _advanced_reranker 