import os
from typing import Dict, Any

class Config:
    """系统配置类"""
    
    # 模型配置
    EMBEDDING_MODEL = "moka-ai/m3e-base"  # 中文文本嵌入模型
    EMBEDDING_DIM = 768
    
    # DeepSeek大模型配置
    DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))
    DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))
    
    # 多表示索引配置
    MULTI_REPRESENTATION_ENABLED = True
    
    # 稠密向量配置
    DENSE_EMBEDDING_MODEL = "moka-ai/m3e-base"  # 中文文本嵌入模型
    DENSE_EMBEDDING_DIM = 768
    
    # 稀疏向量配置（BM25等）
    SPARSE_EMBEDDING_ENABLED = True
    BM25_K1 = 1.2
    BM25_B = 0.75
    
    # 层次化索引配置
    HIERARCHICAL_INDEX_ENABLED = True
    INDEX_LEVELS = {
        "policy": {"chunk_size": 2048, "overlap": 200},      # 政策级别
        "section": {"chunk_size": 1024, "overlap": 100},     # 段落级别  
        "sentence": {"chunk_size": 512, "overlap": 50}       # 句子级别
    }
    
    # 重排配置
    RERANK_ENABLED = True
    RERANK_MODEL = "cross-encoder"  # 跨编码器重排
    RERANK_TOP_K = 100              # 重排前的候选数量
    FINAL_TOP_K = 10                # 最终返回数量
    
    # LLM重排配置
    LLM_RERANK_ENABLED = True
    LLM_RERANK_BATCH_SIZE = 5       # 每批次重排数量
    
    # 提示工程配置
    PROMPT_ENGINEERING_ENABLED = True
    DYNAMIC_PROMPT_OPTIMIZATION = True
    
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
    
    # 行业映射 - 大幅增强
    INDUSTRY_MAPPING = {
        "生物医药": [
            "生物", "医药", "医疗", "制药", "生命科学", "医疗器械", "医药健康",
            "生物技术", "生物制药", "医疗设备", "药品", "医疗器材", "健康产业",
            "医药产业", "生物产业", "医疗健康", "药物研发", "临床试验",
            "医疗服务", "基因", "细胞", "蛋白质", "疫苗", "诊断试剂",
            "医用材料", "康复设备", "体外诊断", "精准医疗", "数字医疗"
        ],
        "信息技术": [
            "信息技术", "IT", "软件", "互联网", "计算机", "数字化",
            "人工智能", "大数据", "云计算", "物联网", "区块链", "5G",
            "软件开发", "信息服务", "数字经济", "网络技术", "电子信息",
            "信息安全", "数据处理", "系统集成", "智能化", "数字产业",
            "网络安全", "数据中心", "芯片", "半导体", "集成电路"
        ],
        "新能源": [
            "新能源", "清洁能源", "太阳能", "风能", "电池", "储能",
            "光伏", "风电", "氢能", "核能", "地热", "生物质能",
            "新能源汽车", "电动汽车", "充电桩", "动力电池", "燃料电池",
            "可再生能源", "绿色能源", "节能", "能源存储"
        ],
        "新材料": [
            "新材料", "材料", "复合材料", "功能材料", "纳米材料",
            "高分子材料", "金属材料", "陶瓷材料", "碳材料", "生物材料",
            "智能材料", "超导材料", "半导体材料", "光电材料", "磁性材料",
            "建筑材料", "包装材料", "化工新材料"
        ],
        "高端装备": [
            "装备制造", "智能制造", "机械", "设备", "制造业", "工业",
            "自动化", "机器人", "数控机床", "工业机器人", "智能装备",
            "精密仪器", "测量设备", "检测设备", "工程机械", "航空装备",
            "船舶装备", "轨道交通装备", "海洋工程装备", "增材制造", "3D打印"
        ],
        "节能环保": [
            "节能", "环保", "绿色", "低碳", "循环经济", "环境保护",
            "污染治理", "废物处理", "水处理", "大气治理", "土壤修复",
            "清洁生产", "资源回收", "环保设备", "环保技术", "环保服务",
            "碳减排", "碳中和", "绿色发展", "可持续发展"
        ],
        "文化创意": [
            "文化", "创意", "设计", "艺术", "传媒", "广告", "影视",
            "动漫", "游戏", "文化产业", "创意产业", "数字创意",
            "文化旅游", "文化传媒", "内容创作", "版权", "知识产权"
        ],
        "现代服务业": [
            "服务业", "金融", "物流", "咨询", "法律", "会计", "商务服务",
            "专业服务", "技术服务", "信息服务", "现代物流", "供应链",
            "电子商务", "平台经济", "共享经济", "数字服务"
        ]
    }
    
    # 初创企业友好指标
    STARTUP_FRIENDLY_INDICATORS = {
        "正面指标": [
            "初创", "创业", "新成立", "新设立", "孵化", "众创", "创新创业",
            "低门槛", "无需", "不限", "灵活", "简化", "便民", "一站式",
            "快速审批", "绿色通道", "优先支持"
        ],
        "负面指标": [
            "三年以上", "五年以上", "成立满", "注册满", "营业满",
            "营业收入.*千万", "营业收入.*亿", "年销售收入.*千万", "年销售收入.*亿",
            "上市公司", "大型企业", "规模以上", "行业龙头", "领军企业"
        ]
    }

# 全局配置实例
config = Config() 