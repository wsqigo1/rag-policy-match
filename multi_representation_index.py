import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pickle
import os
from collections import defaultdict
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from rank_bm25 import BM25Okapi

from config import config
from models import PolicyChunk, RetrievalResult

logger = logging.getLogger(__name__)

class IndexLevel(Enum):
    """索引级别枚举"""
    POLICY = "policy"           # 政策级别（完整政策文档）
    SECTION = "section"         # 段落级别（政策章节）
    SENTENCE = "sentence"       # 句子级别（详细内容）

class RepresentationType(Enum):
    """表示类型枚举"""
    DENSE = "dense"             # 稠密向量（语义表示）
    SPARSE = "sparse"           # 稀疏向量（BM25等）
    KEYWORD = "keyword"         # 关键词表示
    HYBRID = "hybrid"           # 混合表示

@dataclass
class MultiRepresentationChunk:
    """多表示分块数据"""
    chunk_id: str
    policy_id: str
    content: str
    level: IndexLevel
    
    # 多种表示
    dense_embedding: Optional[np.ndarray] = None
    sparse_features: Optional[Dict] = None
    keywords: Optional[List[str]] = None
    tfidf_vector: Optional[np.ndarray] = None
    
    # 层次关系
    parent_id: Optional[str] = None
    children_ids: Optional[List[str]] = None
    
    # 元数据
    section: Optional[str] = None
    importance_score: float = 0.0
    metadata: Optional[Dict] = None

class BM25Indexer:
    """BM25稀疏索引器"""
    
    def __init__(self, k1: float = 1.2, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.bm25 = None
        self.documents = []
        self.chunk_ids = []
    
    def build_index(self, chunks: List[MultiRepresentationChunk]):
        """构建BM25索引"""
        try:
            self.documents = []
            self.chunk_ids = []
            
            for chunk in chunks:
                # 中文分词
                tokens = list(jieba.cut(chunk.content, cut_all=False))
                self.documents.append(tokens)
                self.chunk_ids.append(chunk.chunk_id)
            
            # 构建BM25索引
            self.bm25 = BM25Okapi(self.documents, k1=self.k1, b=self.b)
            logger.info(f"BM25索引构建完成，文档数量: {len(self.documents)}")
            
        except Exception as e:
            logger.error(f"构建BM25索引失败: {e}")
            raise e
    
    def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """BM25搜索"""
        if not self.bm25:
            return []
        
        try:
            # 查询分词
            query_tokens = list(jieba.cut(query, cut_all=False))
            
            # 计算BM25分数
            scores = self.bm25.get_scores(query_tokens)
            
            # 获取top-k结果
            top_indices = np.argsort(scores)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if scores[idx] > 0:  # 只返回有分数的结果
                    results.append((self.chunk_ids[idx], float(scores[idx])))
            
            return results
            
        except Exception as e:
            logger.error(f"BM25搜索失败: {e}")
            return []

class TFIDFIndexer:
    """TF-IDF索引器"""
    
    def __init__(self, max_features: int = 10000):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            tokenizer=lambda x: list(jieba.cut(x, cut_all=False)),
            lowercase=False,
            stop_words=None
        )
        self.tfidf_matrix = None
        self.chunk_ids = []
    
    def build_index(self, chunks: List[MultiRepresentationChunk]):
        """构建TF-IDF索引"""
        try:
            documents = [chunk.content for chunk in chunks]
            self.chunk_ids = [chunk.chunk_id for chunk in chunks]
            
            # 构建TF-IDF矩阵
            self.tfidf_matrix = self.vectorizer.fit_transform(documents)
            
            # 为每个chunk保存TF-IDF向量
            for i, chunk in enumerate(chunks):
                chunk.tfidf_vector = self.tfidf_matrix[i].toarray().flatten()
            
            logger.info(f"TF-IDF索引构建完成，特征数: {self.tfidf_matrix.shape[1]}")
            
        except Exception as e:
            logger.error(f"构建TF-IDF索引失败: {e}")
            raise e
    
    def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """TF-IDF搜索"""
        if self.tfidf_matrix is None:
            return []
        
        try:
            # 查询向量化
            query_vector = self.vectorizer.transform([query])
            
            # 计算余弦相似度
            similarities = (self.tfidf_matrix * query_vector.T).toarray().flatten()
            
            # 获取top-k结果
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0:
                    results.append((self.chunk_ids[idx], float(similarities[idx])))
            
            return results
            
        except Exception as e:
            logger.error(f"TF-IDF搜索失败: {e}")
            return []

class HierarchicalIndexManager:
    """层次化索引管理器"""
    
    def __init__(self):
        # 不同级别的索引
        self.level_indexes = {
            IndexLevel.POLICY: {},
            IndexLevel.SECTION: {},
            IndexLevel.SENTENCE: {}
        }
        
        # 层次关系映射
        self.hierarchy_map = defaultdict(list)  # parent_id -> [children_ids]
        self.reverse_hierarchy = {}  # child_id -> parent_id
        
        # 多表示索引器
        self.bm25_indexers = {}
        self.tfidf_indexers = {}
        
        # 导入重要性权重
        self.importance_weights = {
            IndexLevel.POLICY: 1.0,
            IndexLevel.SECTION: 0.8,
            IndexLevel.SENTENCE: 0.6
        }
    
    def build_hierarchical_chunks(self, policy_chunks: List[PolicyChunk]) -> List[MultiRepresentationChunk]:
        """构建层次化分块"""
        multi_chunks = []
        
        # 按政策ID分组
        policy_groups = defaultdict(list)
        for chunk in policy_chunks:
            policy_groups[chunk.policy_id].append(chunk)
        
        for policy_id, chunks in policy_groups.items():
            # 构建三级层次结构
            policy_level_chunks = self._create_policy_level_chunks(policy_id, chunks)
            section_level_chunks = self._create_section_level_chunks(policy_id, chunks)
            sentence_level_chunks = self._create_sentence_level_chunks(chunks)
            
            multi_chunks.extend(policy_level_chunks)
            multi_chunks.extend(section_level_chunks)
            multi_chunks.extend(sentence_level_chunks)
            
            # 建立层次关系
            self._build_hierarchy_relations(policy_level_chunks, section_level_chunks, sentence_level_chunks)
        
        logger.info(f"构建层次化分块完成，总数: {len(multi_chunks)}")
        return multi_chunks
    
    def _create_policy_level_chunks(self, policy_id: str, chunks: List[PolicyChunk]) -> List[MultiRepresentationChunk]:
        """创建政策级别分块（整个政策的摘要）"""
        # 合并所有内容
        full_content = "\n".join([chunk.content for chunk in chunks])
        
        # 生成政策级别摘要（可以调用LLM生成更好的摘要）
        policy_summary = self._generate_policy_summary(full_content)
        
        chunk = MultiRepresentationChunk(
            chunk_id=f"{policy_id}_policy_level",
            policy_id=policy_id,
            content=policy_summary,
            level=IndexLevel.POLICY,
            importance_score=1.0,
            metadata={"original_chunks_count": len(chunks)}
        )
        
        return [chunk]
    
    def _create_section_level_chunks(self, policy_id: str, chunks: List[PolicyChunk]) -> List[MultiRepresentationChunk]:
        """创建段落级别分块"""
        section_chunks = []
        
        # 按section分组
        section_groups = defaultdict(list)
        for chunk in chunks:
            section = chunk.section or "default"
            section_groups[section].append(chunk)
        
        for section, section_chunk_list in section_groups.items():
            # 合并同一section的内容
            section_content = "\n".join([chunk.content for chunk in section_chunk_list])
            
            # 计算重要性分数（基于长度和关键词密度）
            importance = self._calculate_section_importance(section_content)
            
            chunk = MultiRepresentationChunk(
                chunk_id=f"{policy_id}_section_{section}",
                policy_id=policy_id,
                content=section_content,
                level=IndexLevel.SECTION,
                section=section,
                importance_score=importance,
                metadata={"original_chunks_count": len(section_chunk_list)}
            )
            
            section_chunks.append(chunk)
        
        return section_chunks
    
    def _create_sentence_level_chunks(self, chunks: List[PolicyChunk]) -> List[MultiRepresentationChunk]:
        """创建句子级别分块（原始分块，可能进一步细分）"""
        sentence_chunks = []
        
        for chunk in chunks:
            # 如果原始分块太长，进一步细分
            if len(chunk.content) > config.INDEX_LEVELS["sentence"]["chunk_size"]:
                sub_chunks = self._split_long_chunk(chunk)
                for i, sub_content in enumerate(sub_chunks):
                    sentence_chunk = MultiRepresentationChunk(
                        chunk_id=f"{chunk.chunk_id}_sub_{i}",
                        policy_id=chunk.policy_id,
                        content=sub_content,
                        level=IndexLevel.SENTENCE,
                        section=chunk.section,
                        importance_score=0.6,
                        metadata={"parent_chunk_id": chunk.chunk_id}
                    )
                    sentence_chunks.append(sentence_chunk)
            else:
                # 直接转换
                sentence_chunk = MultiRepresentationChunk(
                    chunk_id=chunk.chunk_id,
                    policy_id=chunk.policy_id,
                    content=chunk.content,
                    level=IndexLevel.SENTENCE,
                    section=chunk.section,
                    importance_score=0.6,
                    metadata={"keywords": chunk.keywords}
                )
                sentence_chunks.append(sentence_chunk)
        
        return sentence_chunks
    
    def _build_hierarchy_relations(self, policy_chunks: List[MultiRepresentationChunk],
                                  section_chunks: List[MultiRepresentationChunk],
                                  sentence_chunks: List[MultiRepresentationChunk]):
        """建立层次关系"""
        # 政策 -> 段落关系
        for policy_chunk in policy_chunks:
            policy_id = policy_chunk.policy_id
            related_sections = [s.chunk_id for s in section_chunks if s.policy_id == policy_id]
            policy_chunk.children_ids = related_sections
            
            for section_id in related_sections:
                self.hierarchy_map[policy_chunk.chunk_id].append(section_id)
                self.reverse_hierarchy[section_id] = policy_chunk.chunk_id
        
        # 段落 -> 句子关系
        for section_chunk in section_chunks:
            policy_id = section_chunk.policy_id
            section = section_chunk.section
            related_sentences = [s.chunk_id for s in sentence_chunks 
                               if s.policy_id == policy_id and s.section == section]
            section_chunk.children_ids = related_sentences
            
            for sentence_id in related_sentences:
                self.hierarchy_map[section_chunk.chunk_id].append(sentence_id)
                self.reverse_hierarchy[sentence_id] = section_chunk.chunk_id
    
    def build_multi_representation_index(self, chunks: List[MultiRepresentationChunk]):
        """构建多表示索引"""
        # 按级别分组
        level_chunks = {level: [] for level in IndexLevel}
        for chunk in chunks:
            level_chunks[chunk.level].append(chunk)
        
        # 为每个级别构建多种索引
        for level, level_chunk_list in level_chunks.items():
            if not level_chunk_list:
                continue
            
            logger.info(f"为{level.value}级别构建索引，分块数: {len(level_chunk_list)}")
            
            # 构建BM25索引
            bm25_indexer = BM25Indexer(k1=config.BM25_K1, b=config.BM25_B)
            bm25_indexer.build_index(level_chunk_list)
            self.bm25_indexers[level] = bm25_indexer
            
            # 构建TF-IDF索引
            tfidf_indexer = TFIDFIndexer()
            tfidf_indexer.build_index(level_chunk_list)
            self.tfidf_indexers[level] = tfidf_indexer
            
            # 存储分块索引
            self.level_indexes[level] = {chunk.chunk_id: chunk for chunk in level_chunk_list}
    
    def hierarchical_search(self, query: str, top_k: int = 50, 
                          level_weights: Optional[Dict[IndexLevel, float]] = None) -> List[RetrievalResult]:
        """层次化搜索"""
        if level_weights is None:
            level_weights = self.importance_weights
        
        all_results = []
        
        # 在每个级别进行搜索
        for level in IndexLevel:
            if level not in self.bm25_indexers:
                continue
            
            level_weight = level_weights.get(level, 1.0)
            
            # BM25搜索
            bm25_results = self.bm25_indexers[level].search(query, top_k)
            
            # TF-IDF搜索
            tfidf_results = self.tfidf_indexers[level].search(query, top_k)
            
            # 合并并加权
            level_results = self._merge_sparse_results(bm25_results, tfidf_results, level_weight)
            
            # 转换为RetrievalResult
            for chunk_id, score in level_results:
                if chunk_id in self.level_indexes[level]:
                    chunk = self.level_indexes[level][chunk_id]
                    result = RetrievalResult(
                        chunk_id=chunk_id,
                        content=chunk.content,
                        score=score,
                        policy_id=chunk.policy_id,
                        metadata={
                            'level': level.value,
                            'section': chunk.section,
                            'importance_score': chunk.importance_score,
                            'source': 'hierarchical_sparse'
                        }
                    )
                    all_results.append(result)
        
        # 去重并排序
        unique_results = self._deduplicate_results(all_results)
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        return unique_results[:top_k]
    
    def get_hierarchy_context(self, chunk_id: str) -> Dict[str, Any]:
        """获取层次上下文"""
        context = {
            "current_chunk": chunk_id,
            "parent": self.reverse_hierarchy.get(chunk_id),
            "children": self.hierarchy_map.get(chunk_id, []),
            "siblings": []
        }
        
        # 获取兄弟节点
        parent_id = context["parent"]
        if parent_id:
            context["siblings"] = [cid for cid in self.hierarchy_map.get(parent_id, []) 
                                  if cid != chunk_id]
        
        return context
    
    def _generate_policy_summary(self, content: str) -> str:
        """生成政策摘要（简化版，可以集成LLM）"""
        # 简单的摘要逻辑：取前500字符
        if len(content) <= 500:
            return content
        
        # 尝试按句子截断
        sentences = content.split('。')
        summary = ""
        for sentence in sentences:
            if len(summary + sentence) <= 500:
                summary += sentence + '。'
            else:
                break
        
        return summary or content[:500]
    
    def _calculate_section_importance(self, content: str) -> float:
        """计算段落重要性"""
        # 基于长度的基础分数
        length_score = min(len(content) / 1000, 1.0)
        
        # 基于关键词的重要性
        important_keywords = ['政策', '支持', '申请', '条件', '资金', '补贴', '要求', '流程']
        keyword_score = sum(1 for keyword in important_keywords if keyword in content) / len(important_keywords)
        
        return 0.6 * length_score + 0.4 * keyword_score
    
    def _split_long_chunk(self, chunk: PolicyChunk) -> List[str]:
        """拆分长分块"""
        content = chunk.content
        max_size = config.INDEX_LEVELS["sentence"]["chunk_size"]
        overlap = config.INDEX_LEVELS["sentence"]["overlap"]
        
        if len(content) <= max_size:
            return [content]
        
        sub_chunks = []
        start = 0
        while start < len(content):
            end = start + max_size
            if end >= len(content):
                sub_chunks.append(content[start:])
                break
            else:
                # 尝试在句号处截断
                period_pos = content.rfind('。', start, end)
                if period_pos > start:
                    end = period_pos + 1
                
                sub_chunks.append(content[start:end])
                start = end - overlap
        
        return sub_chunks
    
    def _merge_sparse_results(self, bm25_results: List[Tuple[str, float]], 
                            tfidf_results: List[Tuple[str, float]], 
                            level_weight: float) -> List[Tuple[str, float]]:
        """合并稀疏搜索结果"""
        score_map = defaultdict(float)
        
        # BM25结果（权重0.6）
        for chunk_id, score in bm25_results:
            score_map[chunk_id] += 0.6 * score * level_weight
        
        # TF-IDF结果（权重0.4）
        for chunk_id, score in tfidf_results:
            score_map[chunk_id] += 0.4 * score * level_weight
        
        # 排序返回
        sorted_results = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
        return sorted_results
    
    def _deduplicate_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """去重结果"""
        seen = set()
        unique_results = []
        
        for result in results:
            if result.chunk_id not in seen:
                seen.add(result.chunk_id)
                unique_results.append(result)
        
        return unique_results
    
    def save_index(self, filepath: str):
        """保存索引"""
        try:
            index_data = {
                'level_indexes': self.level_indexes,
                'hierarchy_map': dict(self.hierarchy_map),
                'reverse_hierarchy': self.reverse_hierarchy,
                'importance_weights': self.importance_weights
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(index_data, f)
            
            logger.info(f"层次索引已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
    
    def load_index(self, filepath: str):
        """加载索引"""
        try:
            with open(filepath, 'rb') as f:
                index_data = pickle.load(f)
            
            self.level_indexes = index_data['level_indexes']
            self.hierarchy_map = defaultdict(list, index_data['hierarchy_map'])
            self.reverse_hierarchy = index_data['reverse_hierarchy']
            self.importance_weights = index_data['importance_weights']
            
            logger.info(f"层次索引已从 {filepath} 加载")
            
        except Exception as e:
            logger.error(f"加载索引失败: {e}")

# 全局层次索引管理器实例
_hierarchical_index_manager = None

def get_hierarchical_index_manager() -> HierarchicalIndexManager:
    """获取层次索引管理器实例"""
    global _hierarchical_index_manager
    if _hierarchical_index_manager is None:
        _hierarchical_index_manager = HierarchicalIndexManager()
    return _hierarchical_index_manager 