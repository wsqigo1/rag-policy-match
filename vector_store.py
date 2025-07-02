import logging
import numpy as np
from typing import List, Dict, Any, Optional
import json

from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError, NotFoundError

from config import config
from models import PolicyChunk, RetrievalResult

logger = logging.getLogger(__name__)

class MilvusStore:
    """Milvus向量数据库操作类"""
    
    def __init__(self):
        self.collection = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """连接到Milvus"""
        try:
            connections.connect(
                alias="default",
                host=config.MILVUS_HOST,
                port=config.MILVUS_PORT
            )
            self.connected = True
            logger.info(f"已连接到Milvus: {config.MILVUS_HOST}:{config.MILVUS_PORT}")
            self._init_collection()
        except Exception as e:
            logger.error(f"连接Milvus失败: {e}")
            self.connected = False
    
    def _init_collection(self):
        """初始化集合"""
        try:
            # 检查集合是否存在
            if utility.has_collection(config.MILVUS_COLLECTION):
                self.collection = Collection(config.MILVUS_COLLECTION)
                logger.info(f"加载现有集合: {config.MILVUS_COLLECTION}")
            else:
                # 创建新集合
                self._create_collection()
            
            # 加载集合到内存
            self.collection.load()
            
        except Exception as e:
            logger.error(f"初始化集合失败: {e}")
            raise e
    
    def _create_collection(self):
        """创建新集合"""
        try:
            # 定义字段 - 顺序必须与插入顺序完全一致
            fields = [
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
                FieldSchema(name="policy_id", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2048),
                FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="chunk_type", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=config.EMBEDDING_DIM)
            ]
            
            # 创建集合schema
            schema = CollectionSchema(
                fields=fields,
                description="政策文档向量集合"
            )
            
            # 创建集合
            self.collection = Collection(
                name=config.MILVUS_COLLECTION,
                schema=schema
            )
            
            # 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            logger.info(f"创建新集合: {config.MILVUS_COLLECTION}")
            
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            raise e
    
    def insert_chunks(self, chunks: List[PolicyChunk], embeddings: np.ndarray):
        """插入文档分块"""
        if not self.connected or not chunks:
            return False
        
        try:
            # 准备数据，严格控制字段长度（按字节计算）
            def safe_truncate(text, max_bytes):
                """安全截断文本，确保不超过最大字节数"""
                if not text:
                    return ""
                text_str = str(text)
                text_bytes = text_str.encode('utf-8')
                if len(text_bytes) <= max_bytes:
                    return text_str
                # 如果超长，按字节截断并确保不切断中文字符
                truncated = text_bytes[:max_bytes]
                # 处理可能的不完整UTF-8字符
                while len(truncated) > 0:
                    try:
                        return truncated.decode('utf-8')
                    except UnicodeDecodeError:
                        truncated = truncated[:-1]
                return ""
            
            chunk_ids = [safe_truncate(chunk.chunk_id, 250) for chunk in chunks]
            policy_ids = [safe_truncate(chunk.policy_id, 250) for chunk in chunks]  
            contents = [safe_truncate(chunk.content, 1900) for chunk in chunks]  # 留足够余量
            sections = [safe_truncate(chunk.section or "", 250) for chunk in chunks]
            chunk_types = [safe_truncate(chunk.chunk_type, 60) for chunk in chunks]
            embedding_list = embeddings.tolist()
            
            # 调试信息
            logger.info(f"准备插入数据: chunks数量={len(chunks)}, embeddings形状={embeddings.shape}")
            logger.info(f"chunk_ids类型: {type(chunk_ids)}, 样例: {chunk_ids[:2] if chunk_ids else []}")
            logger.info(f"embedding_list类型: {type(embedding_list)}, 长度: {len(embedding_list)}")
            
            # 按字段顺序组织数据（列表的列表）
            data_to_insert = [
                chunk_ids,       # 对应字段: chunk_id (VARCHAR)
                policy_ids,      # 对应字段: policy_id (VARCHAR)
                contents,        # 对应字段: content (VARCHAR)
                sections,        # 对应字段: section (VARCHAR)
                chunk_types,     # 对应字段: chunk_type (VARCHAR)
                embedding_list   # 对应字段: embedding (FLOAT_VECTOR)
            ]

            # 验证数据类型
            if not self._validate_data_types(data_to_insert):
                return False

            # 插入数据
            insert_result = self.collection.insert(data_to_insert)

            # 刷新
            self.collection.flush()

            logger.info(f"成功插入 {len(chunks)} 个分块到Milvus")
            return True
        
        except Exception as e:
            logger.error(f"插入数据到Milvus失败: {e}")
            return False

    def _validate_data_types(self, data_list):
        """验证数据类型是否匹配集合模式"""
        if not self.collection:
            return False

        schema = self.collection.schema
        for i, field in enumerate(schema.fields):
            field_name = field.name
            field_type = field.dtype
            sample_value = data_list[i][0] if data_list[i] else None

            logger.info(f"验证字段 {field_name} (Milvus类型: {field_type}) - "
                        f"样例值: {sample_value} - Python类型: {type(sample_value)}")

            # 特殊处理向量字段
            if field_type == DataType.FLOAT_VECTOR:
                if not isinstance(data_list[i], list) or not all(isinstance(vec, list) for vec in data_list[i]):
                    logger.error(f"字段 {field_name} 应为向量列表，实际类型: {type(data_list[i])}")
                    return False
            else:
                # 检查第一个元素的类型
                if data_list[i] and not isinstance(sample_value, self._get_python_type(field_type)):
                    logger.error(
                        f"字段 {field_name} 应为 {self._get_python_type(field_type)}，实际类型: {type(sample_value)}")
                    return False
        return True

    @staticmethod
    def _get_python_type(milvus_type):
        """映射Milvus类型到Python类型"""
        type_map = {
            DataType.VARCHAR: str,
            DataType.INT64: int,
            DataType.FLOAT: float,
            DataType.DOUBLE: float,
            DataType.BOOL: bool,
            DataType.JSON: dict
        }
        return type_map.get(milvus_type, object)

    def search(self, query_embedding: np.ndarray, top_k: int = 10, filters: Dict = None) -> List[RetrievalResult]:
        """向量相似度搜索"""
        if not self.connected:
            return []
        
        try:
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # 构建过滤表达式
            expr = None
            if filters:
                conditions = []
                if filters.get('policy_ids'):
                    policy_ids_str = ', '.join([f'"{pid}"' for pid in filters['policy_ids']])
                    conditions.append(f"policy_id in [{policy_ids_str}]")
                if filters.get('chunk_type'):
                    conditions.append(f'chunk_type == "{filters["chunk_type"]}"')
                
                if conditions:
                    expr = " && ".join(conditions)
            
            # 执行搜索
            results = self.collection.search(
                data=[query_embedding.tolist()],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["chunk_id", "policy_id", "content", "section", "chunk_type"]
            )
            
            # 转换结果
            retrieval_results = []
            if results and len(results) > 0:
                for hit in results[0]:
                    retrieval_results.append(RetrievalResult(
                        chunk_id=hit.entity.get('chunk_id'),
                        content=hit.entity.get('content'),
                        score=float(hit.score),
                        policy_id=hit.entity.get('policy_id'),
                        metadata={
                            'section': hit.entity.get('section'),
                            'chunk_type': hit.entity.get('chunk_type')
                        }
                    ))
            
            logger.info(f"Milvus搜索返回 {len(retrieval_results)} 个结果")
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Milvus搜索失败: {e}")
            return []
    
    def delete_by_policy_id(self, policy_id: str) -> bool:
        """删除指定政策的所有分块"""
        if not self.connected:
            return False
        
        try:
            expr = f'policy_id == "{policy_id}"'
            self.collection.delete(expr)
            self.collection.flush()
            logger.info(f"删除政策 {policy_id} 的所有分块")
            return True
        except Exception as e:
            logger.error(f"删除数据失败: {e}")
            return False
    
    def get_collection_stats(self) -> Dict:
        """获取集合统计信息"""
        if not self.connected:
            return {}
        
        try:
            # 使用num_entities属性获取实体数量
            num_entities = self.collection.num_entities
            return {"row_count": num_entities}
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

class ElasticsearchStore:
    """Elasticsearch操作类"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """连接到Elasticsearch"""
        try:
            self.client = Elasticsearch(
                hosts=[f"http://{config.ES_HOST}:{config.ES_PORT}"],
                request_timeout=30
            )
            
            # 测试连接
            if self.client.ping():
                self.connected = True
                logger.info(f"已连接到Elasticsearch: {config.ES_HOST}:{config.ES_PORT}")
                self._init_index()
            else:
                logger.error("Elasticsearch连接测试失败")
                
        except Exception as e:
            logger.error(f"连接Elasticsearch失败: {e}")
            self.connected = False
    
    def _init_index(self):
        """初始化索引"""
        try:
            # 检查索引是否存在
            if not self.client.indices.exists(index=config.ES_INDEX):
                self._create_index()
            
            logger.info(f"Elasticsearch索引就绪: {config.ES_INDEX}")
            
        except Exception as e:
            logger.error(f"初始化索引失败: {e}")
    
    def _create_index(self):
        """创建索引"""
        try:
            mapping = {
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "policy_id": {"type": "keyword"},
                        "title": {"type": "text", "analyzer": "standard"},
                        "content": {"type": "text", "analyzer": "standard"},
                        "section": {"type": "text", "analyzer": "standard"},
                        "chunk_type": {"type": "keyword"},
                        "keywords": {"type": "keyword"},
                        "industries": {"type": "keyword"},
                        "enterprise_scales": {"type": "keyword"},
                        "policy_types": {"type": "keyword"},
                        "page_num": {"type": "integer"},
                        "created_at": {"type": "date"}
                    }
                },
                "settings": {
                    "analysis": {
                        "analyzer": {
                            "default": {
                                "type": "standard"
                            }
                        }
                    }
                }
            }
            
            self.client.indices.create(
                index=config.ES_INDEX,
                body=mapping
            )
            
            logger.info(f"创建Elasticsearch索引: {config.ES_INDEX}")
            
        except Exception as e:
            logger.error(f"创建索引失败: {e}")
            raise e
    
    def index_chunks(self, chunks: List[PolicyChunk], policy_title: str = "", policy_metadata: Dict = None):
        """索引文档分块"""
        if not self.connected or not chunks:
            return False
        
        try:
            # 安全截断函数，确保不超过ES字段限制
            def safe_truncate_es(text, max_chars=8000):
                """安全截断文本，避免ES字段过长"""
                if not text:
                    return ""
                text_str = str(text)
                if len(text_str) <= max_chars:
                    return text_str
                return text_str[:max_chars]
            
            actions = []
            for chunk in chunks:
                # 确保所有字段长度合适
                doc = {
                    "chunk_id": safe_truncate_es(chunk.chunk_id, 512),
                    "policy_id": safe_truncate_es(chunk.policy_id, 512),
                    "title": safe_truncate_es(policy_title, 1000),
                    "content": safe_truncate_es(chunk.content, 8000),  # ES默认最大8000字符
                    "section": safe_truncate_es(chunk.section, 1000),
                    "chunk_type": safe_truncate_es(chunk.chunk_type, 100),
                    "keywords": chunk.keywords[:50] if chunk.keywords else [],  # 限制关键词数量
                    "page_num": chunk.page_num if chunk.page_num is not None else 0,
                    "created_at": "now"
                }
                
                # 添加政策元数据，同样进行长度控制
                if policy_metadata:
                    doc.update({
                        "industries": (policy_metadata.get('industries', []) or [])[:20],  # 限制数组长度
                        "enterprise_scales": (policy_metadata.get('enterprise_scales', []) or [])[:20],
                        "policy_types": (policy_metadata.get('policy_types', []) or [])[:20]
                    })
                
                actions.append({
                    "_index": config.ES_INDEX,
                    "_id": chunk.chunk_id,
                    "_source": doc
                })
            
            # 批量索引，获取详细错误信息
            try:
                from elasticsearch.helpers import bulk
                logger.info(f"准备索引 {len(actions)} 个文档到ES")
                
                # 使用streaming_bulk获取详细错误信息
                from elasticsearch.helpers import streaming_bulk
                
                success_count = 0
                failed_count = 0
                failed_examples = []
                
                # 直接使用bulk并获取详细错误
                success, failed = bulk(
                    self.client,
                    actions,
                    request_timeout=60,
                    max_retries=3,
                    stats_only=False
                )
                
                success_count = success
                failed_count = len(failed) if failed else 0
                
                if failed_count > 0:
                    logger.error(f"ES索引失败: {failed_count} 个文档失败, {success_count} 个成功")
                    # 显示前3个失败案例的详细错误信息
                    for i, fail_doc in enumerate(failed[:3]):
                        error_detail = fail_doc.get('index', {})
                        doc_id = error_detail.get('_id', 'unknown')
                        error_info = error_detail.get('error', {})
                        error_type = error_info.get('type', 'unknown')
                        error_reason = error_info.get('reason', 'no reason provided')
                        logger.error(f"失败文档 {i+1} (ID: {doc_id}): 类型={error_type}, 原因={error_reason}")
                else:
                    logger.info(f"ES索引完全成功: {success_count} 个文档")
                
                return success_count > 0
                
            except Exception as bulk_error:
                logger.error(f"ES批量索引异常: {bulk_error}")
                return False
            
        except Exception as e:
            logger.error(f"ES索引失败: {e}")
            return False
    
    def search(self, query: str, filters: Dict = None, top_k: int = 10) -> List[RetrievalResult]:
        """关键词搜索"""
        if not self.connected:
            return []
        
        try:
            # 构建查询
            bool_query = {
                "bool": {
                    "should": [
                        {"match": {"content": {"query": query, "boost": 2.0}}},
                        {"match": {"title": {"query": query, "boost": 1.5}}},
                        {"match": {"keywords": {"query": query, "boost": 1.0}}}
                    ],
                    "minimum_should_match": 1
                }
            }
            
            # 添加过滤条件
            if filters:
                bool_query["bool"]["filter"] = []
                
                if filters.get('industries'):
                    bool_query["bool"]["filter"].append({
                        "terms": {"industries": filters['industries']}
                    })
                
                if filters.get('enterprise_scales'):
                    bool_query["bool"]["filter"].append({
                        "terms": {"enterprise_scales": filters['enterprise_scales']}
                    })
                
                if filters.get('policy_types'):
                    bool_query["bool"]["filter"].append({
                        "terms": {"policy_types": filters['policy_types']}
                    })
                
                if filters.get('policy_ids'):
                    bool_query["bool"]["filter"].append({
                        "terms": {"policy_id": filters['policy_ids']}
                    })
            
            # 执行搜索
            response = self.client.search(
                index=config.ES_INDEX,
                body={
                    "query": bool_query,
                    "size": top_k,
                    "sort": [{"_score": {"order": "desc"}}]
                }
            )
            
            # 转换结果
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                results.append(RetrievalResult(
                    chunk_id=source['chunk_id'],
                    content=source['content'],
                    score=float(hit['_score']),
                    policy_id=source['policy_id'],
                    metadata={
                        'title': source.get('title', ''),
                        'section': source.get('section', ''),
                        'chunk_type': source.get('chunk_type', 'text'),
                        'keywords': source.get('keywords', [])
                    }
                ))
            
            logger.info(f"ES搜索返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"ES搜索失败: {e}")
            return []
    
    def delete_by_policy_id(self, policy_id: str) -> bool:
        """删除指定政策的所有文档"""
        if not self.connected:
            return False
        
        try:
            query = {"term": {"policy_id": policy_id}}
            self.client.delete_by_query(
                index=config.ES_INDEX,
                body={"query": query}
            )
            logger.info(f"删除政策 {policy_id} 的所有文档")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    def get_index_stats(self) -> Dict:
        """获取索引统计信息"""
        if not self.connected:
            return {}
        
        try:
            stats = self.client.indices.stats(index=config.ES_INDEX)
            return {
                "doc_count": stats['indices'][config.ES_INDEX]['total']['docs']['count'],
                "store_size": stats['indices'][config.ES_INDEX]['total']['store']['size_in_bytes']
            }
        except Exception as e:
            logger.error(f"获取索引统计失败: {e}")
            return {}

class VectorStore:
    """向量存储统一接口"""
    
    def __init__(self):
        self.milvus = MilvusStore()
        self.elasticsearch = ElasticsearchStore()
    
    def store_policy_chunks(self, chunks: List[PolicyChunk], embeddings: np.ndarray, 
                           policy_title: str = "", policy_metadata: Dict = None) -> bool:
        """存储政策分块到向量库和ES"""
        try:
            # 存储到Milvus（主要存储）
            milvus_success = self.milvus.insert_chunks(chunks, embeddings)
            
            # 存储到Elasticsearch（可选存储）
            es_success = True
            if self.elasticsearch.connected:
                es_success = self.elasticsearch.index_chunks(chunks, policy_title, policy_metadata)
                if not es_success:
                    logger.warning("ES存储失败，但Milvus存储成功，系统继续运行")
            else:
                logger.info("ES未连接，仅使用Milvus存储")
            
            # 只要Milvus成功就算成功
            return milvus_success
            
        except Exception as e:
            logger.error(f"存储政策分块失败: {e}")
            return False
    
    def delete_policy(self, policy_id: str) -> bool:
        """删除政策"""
        milvus_success = self.milvus.delete_by_policy_id(policy_id)
        
        # ES删除是可选的
        if self.elasticsearch.connected:
            es_success = self.elasticsearch.delete_by_policy_id(policy_id)
            if not es_success:
                logger.warning("ES删除失败，但Milvus删除成功")
        
        return milvus_success
    
    def get_status(self) -> Dict:
        """获取存储状态"""
        return {
            "milvus_connected": self.milvus.connected,
            "elasticsearch_connected": self.elasticsearch.connected,
            "milvus_stats": self.milvus.get_collection_stats(),
            "elasticsearch_stats": self.elasticsearch.get_index_stats()
        }

# 延迟创建全局向量存储实例
_vector_store = None

def get_vector_store():
    """获取向量存储实例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

# 为了向后兼容，提供vector_store属性
def __getattr__(name):
    if name == 'vector_store':
        return get_vector_store()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 