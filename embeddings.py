import numpy as np
from typing import List, Union, Optional
import logging
from sentence_transformers import SentenceTransformer
import torch

from config import config

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """向量化管理器"""
    
    def __init__(self):
        self.model: Optional[SentenceTransformer] = None
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
        
        if self.model is None:
            logger.error("模型未加载")
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
            
            # 确保返回numpy数组（convert_to_numpy=True应该已经处理）
            if not isinstance(embeddings, np.ndarray):
                embeddings = np.array(embeddings)
            
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
        
        if self.model is None:
            logger.error("模型未加载")
            return np.zeros(config.EMBEDDING_DIM)
        
        try:
            embedding = self.model.encode(
                [text.strip()], 
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            
            # 确保返回numpy数组（convert_to_numpy=True应该已经处理）
            if not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding)
            
            return embedding[0] if len(embedding.shape) > 1 else embedding
            
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
        智能查询扩展：基于自然语言理解生成语义相似的查询词
        
        Args:
            query: 原始查询
            
        Returns:
            扩展后的查询列表
        """
        expanded_queries = [query]
        query_lower = query.lower()
        
        # 1. 基于意图的查询扩展
        intent_expansions = self._expand_by_intent(query_lower)
        expanded_queries.extend(intent_expansions)
        
        # 2. 基于行业的查询扩展
        industry_expansions = self._expand_by_industry(query_lower)
        expanded_queries.extend(industry_expansions)
        
        # 3. 基于企业规模的查询扩展  
        scale_expansions = self._expand_by_enterprise_scale(query_lower)
        expanded_queries.extend(scale_expansions)
        
        # 4. 基于政策类型的查询扩展
        policy_expansions = self._expand_by_policy_type(query_lower)
        expanded_queries.extend(policy_expansions)
        
        # 5. 基于同义词的扩展
        synonym_expansions = self._expand_by_synonyms(query_lower)
        expanded_queries.extend(synonym_expansions)
        
        # 去重并返回
        unique_queries = []
        for q in expanded_queries:
            if q not in unique_queries and len(q.strip()) > 0:
                unique_queries.append(q)
        
        return unique_queries[:10]  # 限制扩展查询数量
    
    def _expand_by_intent(self, query: str) -> List[str]:
        """基于用户意图扩展查询"""
        expansions = []
        
        # 查找政策意图
        if any(word in query for word in ['查找', '寻找', '想要', '需要', '有什么', '哪些']):
            expansions.extend(['政策支持', '扶持政策', '优惠政策'])
        
        # 适用性意图
        if any(word in query for word in ['适用', '适合', '可以申请', '符合条件']):
            expansions.extend(['申请条件', '适用范围', '服务对象'])
        
        # 资金支持意图
        if any(word in query for word in ['资金', '补贴', '奖励', '资助', '支持']):
            expansions.extend(['专项资金', '财政支持', '资金扶持', '补助资金'])
        
        return expansions
    
    def _expand_by_industry(self, query: str) -> List[str]:
        """基于行业扩展查询"""
        expansions = []
        
        for industry, keywords in config.INDUSTRY_MAPPING.items():
            for keyword in keywords:
                if keyword in query:
                    # 添加同行业的其他关键词
                    expansions.extend([k for k in keywords if k != keyword])
                    # 添加行业相关的政策词汇
                    expansions.append(f"{industry}政策")
                    expansions.append(f"{industry}扶持")
                    break
        
        return expansions
    
    def _expand_by_enterprise_scale(self, query: str) -> List[str]:
        """基于企业规模扩展查询"""
        expansions = []
        
        for scale, keywords in config.ENTERPRISE_SCALES.items():
            for keyword in keywords:
                if keyword in query:
                    # 添加同规模的其他表述
                    expansions.extend([k for k in keywords if k != keyword])
                    
                    # 针对初创企业的特殊扩展
                    if scale == "初创企业":
                        expansions.extend([
                            '创业扶持', '创业支持', '新企业政策', 
                            '创业孵化', '创业园区', '低门槛政策'
                        ])
                    break
        
        return expansions
    
    def _expand_by_policy_type(self, query: str) -> List[str]:
        """基于政策类型扩展查询"""
        expansions = []
        
        for policy_type, keywords in config.POLICY_TYPES.items():
            for keyword in keywords:
                if keyword in query:
                    # 添加同类型的其他关键词
                    expansions.extend([k for k in keywords if k != keyword])
                    break
        
        return expansions
    
    def _expand_by_synonyms(self, query: str) -> List[str]:
        """基于同义词扩展查询"""
        synonym_map = {
            '公司': ['企业', '机构', '单位'],
            '企业': ['公司', '机构', '单位'],
            '政策': ['措施', '办法', '规定', '条例'],
            '支持': ['扶持', '帮助', '援助'],
            '申请': ['申报', '报名', '参与'],
            '条件': ['要求', '标准', '资格'],
            '资金': ['资助', '补贴', '奖励', '拨款'],
            '创新': ['科技', '技术', '研发'],
            '小型': ['小微', '中小'],
            '初创': ['新成立', '创业', '起步']
        }
        
        expansions = []
        for word, synonyms in synonym_map.items():
            if word in query:
                expansions.extend(synonyms)
        
        return expansions
    
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