import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from config import config

logger = logging.getLogger(__name__)

@dataclass
class QueryIntent:
    """查询意图"""
    intent_type: str  # 'find_policy', 'check_eligibility', 'get_requirements' 等
    confidence: float
    keywords: List[str]

@dataclass
class EntityExtraction:
    """实体提取结果"""
    industries: List[str]
    enterprise_scales: List[str]
    policy_types: List[str]
    regions: List[str]
    amount_requirements: List[str]
    time_requirements: List[str]
    special_conditions: List[str]

@dataclass
class QueryUnderstanding:
    """查询理解结果"""
    original_query: str
    processed_query: str
    primary_intent: QueryIntent
    secondary_intents: List[QueryIntent]
    entities: EntityExtraction
    filters: Dict[str, Any]
    natural_language_context: str
    query_complexity: str  # 'simple', 'moderate', 'complex'

class IntelligentQueryProcessor:
    """智能查询处理器"""
    
    def __init__(self):
        self.intent_patterns = self._build_intent_patterns()
        self.entity_patterns = self._build_entity_patterns()
        self.filter_rules = self._build_filter_rules()
    
    def process_query(self, query: str) -> QueryUnderstanding:
        """
        处理自然语言查询
        
        Args:
            query: 原始查询文本
            
        Returns:
            查询理解结果
        """
        logger.info(f"开始处理自然语言查询: {query}")
        
        # 1. 查询预处理
        processed_query = self._preprocess_query(query)
        
        # 2. 意图识别
        primary_intent, secondary_intents = self._extract_intents(processed_query)
        
        # 3. 实体提取
        entities = self._extract_entities(processed_query)
        
        # 4. 构建过滤条件
        filters = self._build_smart_filters(entities, primary_intent)
        
        # 5. 生成自然语言上下文
        nl_context = self._generate_context(primary_intent, entities)
        
        # 6. 评估查询复杂度
        complexity = self._assess_complexity(query, entities, len(secondary_intents))
        
        result = QueryUnderstanding(
            original_query=query,
            processed_query=processed_query,
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            entities=entities,
            filters=filters,
            natural_language_context=nl_context,
            query_complexity=complexity
        )
        
        logger.info(f"查询理解完成，主要意图: {primary_intent.intent_type}, 复杂度: {complexity}")
        return result
    
    def _preprocess_query(self, query: str) -> str:
        """查询预处理"""
        # 标准化常见表述
        replacements = {
            '我们公司': '企业',
            '我们企业': '企业', 
            '我司': '企业',
            '本公司': '企业',
            '咱们': '我们',
            '有没有': '有什么',
            '能不能': '可以',
            '行不行': '可以',
            '怎么样': '如何',
            '多少钱': '金额',
            '要多少': '金额要求'
        }
        
        processed = query
        for old, new in replacements.items():
            processed = processed.replace(old, new)
        
        return processed.strip()
    
    def _build_intent_patterns(self) -> Dict[str, List[Dict]]:
        """构建意图识别模式"""
        patterns = {
            'find_policy': [
                {'pattern': r'查找|寻找|找|搜索.*政策', 'weight': 0.9},
                {'pattern': r'有什么.*政策|哪些.*政策', 'weight': 0.8},
                {'pattern': r'政策.*有关|关于.*政策', 'weight': 0.7},
                {'pattern': r'想要.*政策|需要.*政策', 'weight': 0.8},
                {'pattern': r'.*相关.*政策', 'weight': 0.7}
            ],
            'check_eligibility': [
                {'pattern': r'适用|适合|符合|匹配', 'weight': 0.9},
                {'pattern': r'可以申请|能申请|能够申请', 'weight': 0.8},
                {'pattern': r'条件.*满足|满足.*条件', 'weight': 0.8},
                {'pattern': r'现阶段.*政策|阶段.*适用', 'weight': 0.7},
                {'pattern': r'比较适用|比较合适', 'weight': 0.9}
            ],
            'get_requirements': [
                {'pattern': r'申请条件|申报条件|条件要求', 'weight': 0.9},
                {'pattern': r'需要.*条件|要求.*什么', 'weight': 0.8},
                {'pattern': r'怎么申请|如何申请|申请流程', 'weight': 0.7}
            ],
            'get_funding': [
                {'pattern': r'资金.*支持|资金.*补贴|资金.*政策', 'weight': 0.9},
                {'pattern': r'补贴.*政策|奖励.*政策|资助.*政策', 'weight': 0.8},
                {'pattern': r'资金.*方面|财政.*支持', 'weight': 0.7}
            ]
        }
        return patterns
    
    def _build_entity_patterns(self) -> Dict[str, List[Dict]]:
        """构建实体识别模式"""
        patterns = {
            'enterprise_scale': [
                {'pattern': r'初创|创业|新成立|起步', 'entity': '初创企业', 'weight': 0.9},
                {'pattern': r'小型|小企业|小微', 'entity': '小型企业', 'weight': 0.9},
                {'pattern': r'中型|中等规模', 'entity': '中型企业', 'weight': 0.9},
                {'pattern': r'大型|大企业|规模企业', 'entity': '大型企业', 'weight': 0.9}
            ],
            'industry': [
                {'pattern': r'生物医药|医药|生物|制药|医疗', 'entity': '生物医药', 'weight': 0.9},
                {'pattern': r'信息技术|IT|软件|互联网|计算机', 'entity': '信息技术', 'weight': 0.9},
                {'pattern': r'新能源|清洁能源|太阳能|风能', 'entity': '新能源', 'weight': 0.9},
                {'pattern': r'新材料|材料|复合材料', 'entity': '新材料', 'weight': 0.9},
                {'pattern': r'高端装备|装备制造|智能制造', 'entity': '高端装备', 'weight': 0.9},
                {'pattern': r'节能环保|环保|绿色|低碳', 'entity': '节能环保', 'weight': 0.9}
            ],
            'policy_type': [
                {'pattern': r'资金|补贴|奖励|资助|专项资金', 'entity': '资金支持', 'weight': 0.8},
                {'pattern': r'税收|减税|免税|税务|优惠', 'entity': '税收优惠', 'weight': 0.8},
                {'pattern': r'人才|专家|引进|培养', 'entity': '人才政策', 'weight': 0.8},
                {'pattern': r'创新|研发|技术|专利|科技', 'entity': '创新支持', 'weight': 0.8},
                {'pattern': r'产业|制造|升级|转型', 'entity': '产业扶持', 'weight': 0.8}
            ]
        }
        return patterns
    
    def _build_filter_rules(self) -> Dict[str, Any]:
        """构建过滤规则"""
        return {
            'startup_friendly_keywords': [
                '低门槛', '无需', '不限', '新企业', '创业扶持', '孵化'
            ],
            'startup_exclude_keywords': [
                '三年以上', '五年以上', '营业收入.*千万', '营业收入.*亿',
                '上市公司', '大型企业', '规模以上'
            ],
            'amount_patterns': [
                r'不超过(\d+)万', r'最高(\d+)万', r'(\d+)万元以下'
            ]
        }
    
    def _extract_intents(self, query: str) -> Tuple[QueryIntent, List[QueryIntent]]:
        """提取查询意图"""
        intent_scores = {}
        
        for intent_type, patterns in self.intent_patterns.items():
            score = 0.0
            matched_keywords = []
            
            for pattern_info in patterns:
                match = re.search(pattern_info['pattern'], query, re.IGNORECASE)
                if match:
                    score += pattern_info['weight']
                    matched_keywords.append(match.group())
            
            if score > 0:
                intent_scores[intent_type] = {
                    'score': score,
                    'keywords': matched_keywords
                }
        
        # 确定主要意图
        if intent_scores:
            primary_type = max(intent_scores.keys(), key=lambda x: intent_scores[x]['score'])
            primary_intent = QueryIntent(
                intent_type=primary_type,
                confidence=min(intent_scores[primary_type]['score'], 1.0),
                keywords=intent_scores[primary_type]['keywords']
            )
            
            # 确定次要意图
            secondary_intents = []
            for intent_type, info in intent_scores.items():
                if intent_type != primary_type and info['score'] > 0.3:
                    secondary_intents.append(QueryIntent(
                        intent_type=intent_type,
                        confidence=min(info['score'], 1.0),
                        keywords=info['keywords']
                    ))
        else:
            # 默认意图
            primary_intent = QueryIntent(
                intent_type='find_policy',
                confidence=0.5,
                keywords=[]
            )
            secondary_intents = []
        
        return primary_intent, secondary_intents
    
    def _extract_entities(self, query: str) -> EntityExtraction:
        """提取实体信息"""
        entities = EntityExtraction(
            industries=[],
            enterprise_scales=[],
            policy_types=[],
            regions=[],
            amount_requirements=[],
            time_requirements=[],
            special_conditions=[]
        )
        
        # 提取企业规模
        for pattern_info in self.entity_patterns['enterprise_scale']:
            if re.search(pattern_info['pattern'], query, re.IGNORECASE):
                entities.enterprise_scales.append(pattern_info['entity'])
        
        # 提取行业信息
        for pattern_info in self.entity_patterns['industry']:
            if re.search(pattern_info['pattern'], query, re.IGNORECASE):
                entities.industries.append(pattern_info['entity'])
        
        # 提取政策类型
        for pattern_info in self.entity_patterns['policy_type']:
            if re.search(pattern_info['pattern'], query, re.IGNORECASE):
                entities.policy_types.append(pattern_info['entity'])
        
        # 提取金额要求
        amount_patterns = [
            r'(\d+)万.*以下',
            r'不超过(\d+)万',
            r'最高(\d+)万',
            r'(\d+)万元.*支持'
        ]
        for pattern in amount_patterns:
            matches = re.findall(pattern, query)
            entities.amount_requirements.extend([f"{m}万元" for m in matches])
        
        # 去重
        entities.industries = list(set(entities.industries))
        entities.enterprise_scales = list(set(entities.enterprise_scales))
        entities.policy_types = list(set(entities.policy_types))
        entities.amount_requirements = list(set(entities.amount_requirements))
        
        return entities
    
    def _build_smart_filters(self, entities: EntityExtraction, 
                           primary_intent: QueryIntent) -> Dict[str, Any]:
        """构建智能过滤条件"""
        filters = {}
        
        # 基础实体过滤
        if entities.industries:
            filters['industries'] = entities.industries
        
        if entities.enterprise_scales:
            filters['enterprise_scales'] = entities.enterprise_scales
        
        if entities.policy_types:
            filters['policy_types'] = entities.policy_types
        
        # 智能过滤规则
        if '初创企业' in entities.enterprise_scales:
            # 对初创企业友好的过滤
            filters['prefer_startup_friendly'] = True
            filters['exclude_high_barrier'] = True
        
        # 根据意图调整过滤
        if primary_intent.intent_type == 'get_funding':
            if 'policy_types' not in filters:
                filters['policy_types'] = ['资金支持']
        
        return filters
    
    def _generate_context(self, primary_intent: QueryIntent, 
                         entities: EntityExtraction) -> str:
        """生成自然语言上下文"""
        context_parts = []
        
        # 意图描述
        intent_descriptions = {
            'find_policy': '寻找相关政策',
            'check_eligibility': '检查政策适用性',
            'get_requirements': '了解申请条件',
            'get_funding': '寻找资金支持'
        }
        context_parts.append(intent_descriptions.get(primary_intent.intent_type, '政策查询'))
        
        # 实体描述
        if entities.enterprise_scales:
            context_parts.append(f"企业规模: {', '.join(entities.enterprise_scales)}")
        
        if entities.industries:
            context_parts.append(f"行业领域: {', '.join(entities.industries)}")
        
        if entities.policy_types:
            context_parts.append(f"政策类型: {', '.join(entities.policy_types)}")
        
        return " | ".join(context_parts)
    
    def _assess_complexity(self, query: str, entities: EntityExtraction, 
                          secondary_intent_count: int) -> str:
        """评估查询复杂度"""
        complexity_score = 0
        
        # 查询长度
        if len(query) > 50:
            complexity_score += 1
        
        # 实体数量
        total_entities = (len(entities.industries) + len(entities.enterprise_scales) + 
                         len(entities.policy_types) + len(entities.amount_requirements))
        if total_entities > 3:
            complexity_score += 2
        elif total_entities > 1:
            complexity_score += 1
        
        # 次要意图数量
        complexity_score += secondary_intent_count
        
        # 特殊条件
        special_patterns = ['现阶段', '比较', '具体', '详细', '怎么', '如何']
        for pattern in special_patterns:
            if pattern in query:
                complexity_score += 1
        
        if complexity_score >= 4:
            return 'complex'
        elif complexity_score >= 2:
            return 'moderate'
        else:
            return 'simple'

# 全局查询处理器实例
_query_processor = None

def get_query_processor():
    """获取查询处理器实例"""
    global _query_processor
    if _query_processor is None:
        _query_processor = IntelligentQueryProcessor()
    return _query_processor 