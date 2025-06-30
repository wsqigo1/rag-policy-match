import numpy as np
from typing import List, Union
import logging
from sentence_transformers import SentenceTransformer
import torch

from config import config

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """向量化管理器"""
    
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self):
        """加载嵌入模型"""
        try:
            logger.info(f"正在加载嵌入模型: {config.EMBEDDING_MODEL}")
            self.model = SentenceTransformer(config.EMBEDDING_MODEL, device=self.device)
            logger.info(f"模型加载完成，使用设备: {self.device}")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            # 如果指定模型加载失败，尝试使用备用模型
            try:
                logger.info("尝试加载备用模型...")
                self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', device=self.device)
                logger.info("备用模型加载成功")
            except Exception as e2:
                logger.error(f"备用模型也加载失败: {e2}")
                raise e2
    
    def encode_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        批量编码文本为向量
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
            
        Returns:
            向量数组
        """
        if not texts:
            return np.array([])
        
        try:
            logger.info(f"开始编码 {len(texts)} 个文本")
            
            # 过滤空文本
            valid_texts = [text.strip() for text in texts if text and text.strip()]
            if not valid_texts:
                logger.warning("所有文本为空")
                return np.array([])
            
            # 批量编码
            embeddings = self.model.encode(
                valid_texts, 
                batch_size=batch_size,
                show_progress_bar=len(valid_texts) > 100,
                convert_to_numpy=True,
                normalize_embeddings=True  # 归一化向量
            )
            
            logger.info(f"编码完成，输出形状: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            logger.error(f"文本编码失败: {e}")
            raise e
    
    def encode_single_text(self, text: str) -> np.ndarray:
        """
        编码单个文本
        
        Args:
            text: 输入文本
            
        Returns:
            向量数组
        """
        if not text or not text.strip():
            return np.zeros(config.EMBEDDING_DIM)
        
        try:
            embedding = self.model.encode(
                [text.strip()], 
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embedding[0]
            
        except Exception as e:
            logger.error(f"单文本编码失败: {e}")
            return np.zeros(config.EMBEDDING_DIM)
    
    def compute_similarity(self, query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
        """
        计算查询向量与文档向量的相似度
        
        Args:
            query_embedding: 查询向量
            doc_embeddings: 文档向量矩阵
            
        Returns:
            相似度分数数组
        """
        try:
            # 使用余弦相似度
            if len(query_embedding.shape) == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # 计算点积（由于向量已归一化，点积等于余弦相似度）
            similarities = np.dot(doc_embeddings, query_embedding.T).flatten()
            
            # 确保相似度在[0, 1]范围内
            similarities = np.clip(similarities, 0, 1)
            
            return similarities
            
        except Exception as e:
            logger.error(f"相似度计算失败: {e}")
            return np.zeros(len(doc_embeddings))
    
    def expand_query(self, query: str) -> List[str]:
        """
        查询扩展：生成语义相似的查询词
        
        Args:
            query: 原始查询
            
        Returns:
            扩展后的查询列表
        """
        expanded_queries = [query]
        
        # 基于配置的映射进行查询扩展
        query_lower = query.lower()
        
        # 行业扩展
        for industry, keywords in config.INDUSTRY_MAPPING.items():
            for keyword in keywords:
                if keyword in query_lower:
                    # 添加同义词
                    expanded_queries.extend([k for k in keywords if k != keyword and k not in expanded_queries])
                    break
        
        # 企业规模扩展
        for scale, keywords in config.ENTERPRISE_SCALES.items():
            for keyword in keywords:
                if keyword in query_lower:
                    expanded_queries.extend([k for k in keywords if k != keyword and k not in expanded_queries])
                    break
        
        # 政策类型扩展
        for policy_type, keywords in config.POLICY_TYPES.items():
            for keyword in keywords:
                if keyword in query_lower:
                    expanded_queries.extend([k for k in keywords if k != keyword and k not in expanded_queries])
                    break
        
        return list(set(expanded_queries))
    
    def get_model_info(self) -> dict:
        """获取模型信息"""
        if not self.model:
            return {"status": "not_loaded"}
        
        return {
            "status": "loaded",
            "model_name": config.EMBEDDING_MODEL,
            "device": self.device,
            "embedding_dim": config.EMBEDDING_DIM,
            "max_seq_length": getattr(self.model, 'max_seq_length', 'unknown')
        }

# 延迟创建全局嵌入管理器实例
_embedding_manager = None

def get_embedding_manager():
    """获取嵌入管理器实例"""
    global _embedding_manager
    if _embedding_manager is None:
        _embedding_manager = EmbeddingManager()
    return _embedding_manager

# 为了向后兼容，提供embedding_manager属性
def __getattr__(name):
    if name == 'embedding_manager':
        return get_embedding_manager()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 