import os
from typing import Dict, Any

class Config:
    """系统配置类"""
    
    # 模型配置
    EMBEDDING_MODEL = "moka-ai/m3e-base"  # 中文文本嵌入模型
    EMBEDDING_DIM = 768
    
    # Milvus配置
    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
    MILVUS_COLLECTION = "policy_collection"
    
    # Elasticsearch配置
    ES_HOST = os.getenv("ES_HOST", "localhost")
    ES_PORT = os.getenv("ES_PORT", "9200")
    ES_INDEX = "policy_index"
    
    # Redis配置
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = os.getenv("REDIS_PORT", "6379")
    REDIS_DB = 0
    
    # 检索配置
    MAX_CHUNK_SIZE = 512
    CHUNK_OVERLAP = 50
    TOP_K_RETRIEVAL = 50
    TOP_K_RERANK = 10
    
    # 文档处理配置
    SUPPORTED_FORMATS = [".pdf", ".docx", ".txt"]
    
    # 政策类型映射
    POLICY_TYPES = {
        "资金支持": ["补贴", "资助", "奖励", "专项资金", "资金支持"],
        "税收优惠": ["税收", "减税", "免税", "税务", "优惠政策"],
        "人才政策": ["人才", "专家", "引进", "培养", "团队"],
        "创新支持": ["创新", "研发", "技术", "专利", "科技"],
        "产业扶持": ["产业", "制造", "升级", "转型", "发展"]
    }
    
    # 企业规模映射
    ENTERPRISE_SCALES = {
        "初创企业": ["初创", "新成立", "创业", "起步"],
        "小型企业": ["小型", "小企业", "小微"],
        "中型企业": ["中型", "中等规模"],
        "大型企业": ["大型", "大企业", "规模企业"]
    }
    
    # 行业映射
    INDUSTRY_MAPPING = {
        "生物医药": ["生物", "医药", "医疗", "制药", "生命科学", "医疗器械", "医药健康"],
        "信息技术": ["信息技术", "IT", "软件", "互联网", "计算机", "数字化"],
        "新能源": ["新能源", "清洁能源", "太阳能", "风能", "电池"],
        "新材料": ["新材料", "材料", "复合材料", "功能材料"],
        "高端装备": ["装备制造", "智能制造", "机械", "设备"],
        "节能环保": ["节能", "环保", "绿色", "低碳", "循环经济"]
    }

# 全局配置实例
config = Config() 