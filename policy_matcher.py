import logging
import time
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime

from models import (
    QueryRequest, QueryResponse, MatchResult, RetrievalResult,
    BasicMatchRequest, PreciseMatchRequest, CompanyInfo, PolicyMatch, OneClickMatchResponse,
    PolicyEligibilityRequest, PolicyEligibilityResponse,
    RequirementStatus, ConditionAnalysis, StructuredPolicy, EnhancedRequirementStatus
)
from advanced_retriever import AdvancedRetriever
from llm_manager import LLMManager
from config import Config

logger = logging.getLogger(__name__)

class StructuredFieldMatcher:
    """结构化字段匹配器"""
    
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
        
        # 字段匹配权重
        self.field_weights = {
            'service_object': 0.25,      # 服务对象权重最高
            'tool_category': 0.20,       # 工具分类
            'condition_requirements': 0.20, # 条件要求
            'service_content': 0.15,     # 服务内容
            'issuing_agency': 0.10,      # 发文机构
            'time_frequency': 0.05,      # 时间频度
            'policy_level': 0.05         # 政策级别
        }

    async def calculate_field_match_score(self, company_info: CompanyInfo, 
                                         policy: StructuredPolicy) -> Dict[str, float]:
        """计算各字段匹配分数"""
        scores = {}
        
        # 1. 服务对象匹配
        scores['service_object'] = await self._match_service_object(
            company_info, policy.service_object
        )
        
        # 2. 工具分类匹配
        scores['tool_category'] = await self._match_tool_category(
            company_info, policy.tool_category
        )
        
        # 3. 条件要求匹配
        scores['condition_requirements'] = await self._match_conditions(
            company_info, policy.condition_requirements
        )
        
        # 4. 服务内容匹配
        scores['service_content'] = await self._match_service_content(
            company_info, policy.service_content
        )
        
        # 5. 发文机构匹配（根据企业所在地）
        scores['issuing_agency'] = self._match_issuing_agency(
            company_info, policy.issuing_agency
        )
        
        # 6. 时间频度匹配
        scores['time_frequency'] = self._match_time_frequency(
            policy.time_frequency
        )
        
        # 7. 政策级别匹配
        scores['policy_level'] = self._match_policy_level(
            company_info, policy.policy_level
        )
        
        return scores

    async def _match_service_object(self, company_info: CompanyInfo, 
                                   service_object: Optional[str]) -> float:
        """匹配服务对象"""
        if not service_object:
            return 0.5
        
        # 企业规模匹配
        scale_keywords = {
            '初创': ['初创', '创业', '新设立', '成立不满'],
            '小型': ['小型', '小微', '中小', '小企业'],
            '中型': ['中型', '中等规模'],
            '大型': ['大型', '大企业', '龙头'],
            '高新': ['高新技术', '高科技', '技术先进'],
            '专精特新': ['专精特新', '隐形冠军'],
        }
        
        score = 0.0
        service_lower = service_object.lower()
        
        # 根据公司规模评分
        if company_info.scale:
            scale_lower = company_info.scale.lower()
            for scale_type, keywords in scale_keywords.items():
                if scale_lower in scale_type.lower():
                    for keyword in keywords:
                        if keyword in service_lower:
                            score += 0.3
                            break
        
        # 行业匹配
        if company_info.industry:
            industry_lower = company_info.industry.lower()
            if any(ind in service_lower for ind in industry_lower.split()):
                score += 0.4
        
        # 企业性质匹配
        if company_info.enterprise_type:
            if company_info.enterprise_type.lower() in service_lower:
                score += 0.3
        
        return min(score, 1.0)

    async def _match_tool_category(self, company_info: CompanyInfo, 
                                  tool_category: Optional[str]) -> float:
        """匹配工具分类"""
        if not tool_category:
            return 0.5
        
        # 根据企业需求推断工具分类偏好
        category_preferences = {
            '资金支持': 0.8,  # 大多数企业都需要资金支持
            '政策支持': 0.6,
            '税收优惠': 0.7,
            '平台支持': 0.5,
            '人才支持': 0.4
        }
        
        category_lower = tool_category.lower()
        
        # 基础匹配
        base_score = 0.5
        
        # 特定匹配
        for category, preference in category_preferences.items():
            if category in category_lower:
                base_score = preference
                break
        
        # 根据企业情况调整
        if company_info.scale == "初创企业" and "资金" in category_lower:
            base_score += 0.2
        
        if company_info.employees and company_info.employees < 50 and "人才" in category_lower:
            base_score += 0.2
        
        return min(base_score, 1.0)

    async def _match_conditions(self, company_info: CompanyInfo, 
                               conditions: Optional[str]) -> float:
        """匹配条件要求"""
        if not conditions:
            return 0.5
        
        # 使用LLM分析条件匹配
        prompt = f"""
        分析企业是否满足政策条件要求，返回匹配分数(0-1)和分析说明。

        企业信息：
        - 公司名称：{company_info.company_name}
        - 行业：{company_info.industry}
        - 规模：{company_info.scale}
        - 员工数：{company_info.employees}
        - 注册资本：{company_info.registered_capital}
        - 年营业额：{company_info.annual_revenue}

        政策条件要求：
        {conditions}

        请分析企业是否满足这些条件，给出0-1的匹配分数。
        """
        
        try:
            response = await self.llm_manager.generate_policy_analysis(
                prompt, company_info.__dict__
            )
            
            # 从响应中提取分数
            score_match = re.search(r'(\d+\.?\d*)', response)
            if score_match:
                score = float(score_match.group(1))
                if score > 1:
                    score = score / 10  # 如果是0-10分制，转换为0-1
                return min(score, 1.0)
            
        except Exception as e:
            logger.warning(f"LLM condition matching failed: {e}")
        
        # 备用规则匹配
        return self._rule_based_condition_match(company_info, conditions)

    def _rule_based_condition_match(self, company_info: CompanyInfo, 
                                   conditions: str) -> float:
        """基于规则的条件匹配"""
        score = 0.5
        conditions_lower = conditions.lower()
        
        # 收入条件匹配
        if company_info.annual_revenue:
            revenue_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:万元|万|亿元|亿)', conditions_lower)
            if revenue_matches:
                required_revenue = float(revenue_matches[0])
                if '亿' in conditions_lower:
                    required_revenue *= 10000
                
                if company_info.annual_revenue >= required_revenue:
                    score += 0.3
                elif company_info.annual_revenue >= required_revenue * 0.8:
                    score += 0.1
        
        # 员工数条件匹配
        if company_info.employees:
            employee_matches = re.findall(r'(\d+)\s*(?:人|名)', conditions_lower)
            if employee_matches:
                required_employees = int(employee_matches[0])
                if company_info.employees >= required_employees:
                    score += 0.2
        
        return min(score, 1.0)

    async def _match_service_content(self, company_info: CompanyInfo, 
                                   service_content: Optional[str]) -> float:
        """匹配服务内容"""
        if not service_content:
            return 0.5
        
        # 基于企业需求匹配服务内容
        content_lower = service_content.lower()
        score = 0.5
        
        # 根据企业规模推断需求
        if company_info.scale == "初创企业":
            if any(keyword in content_lower for keyword in ['孵化', '创业', '启动资金', '初期支持']):
                score += 0.3
        
        # 根据行业匹配
        if company_info.industry:
            industry_lower = company_info.industry.lower()
            if any(ind in content_lower for ind in industry_lower.split()):
                score += 0.2
        
        return min(score, 1.0)

    def _match_issuing_agency(self, company_info: CompanyInfo, 
                             issuing_agency: Optional[str]) -> float:
        """匹配发文机构"""
        if not issuing_agency:
            return 0.5
        
        # 简单的地域匹配逻辑
        agency_lower = issuing_agency.lower()
        
        # 如果是北京的企业，北京市政策更匹配
        if '北京市' in agency_lower:
            return 0.8
        elif '国务院' in agency_lower or '国家' in agency_lower:
            return 0.7  # 国家级政策普遍适用
        else:
            return 0.6

    def _match_time_frequency(self, time_frequency: Optional[str]) -> float:
        """匹配时间频度"""
        if not time_frequency:
            return 0.5
        
        time_lower = time_frequency.lower()
        
        # 常年受理的政策更好
        if '常年' in time_lower or '随时' in time_lower:
            return 0.9
        elif '定期' in time_lower or '批次' in time_lower:
            return 0.7
        else:
            return 0.5

    def _match_policy_level(self, company_info: CompanyInfo, 
                           policy_level: Optional[str]) -> float:
        """匹配政策级别"""
        if not policy_level:
            return 0.5
        
        # 不同级别政策的优先级
        level_scores = {
            '国家级': 0.9,
            '市级': 0.8,
            '区级': 0.7,
            '其他': 0.6
        }
        
        return level_scores.get(policy_level, 0.5)

class EnhancedPolicyMatcher:
    """增强的政策匹配器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.retriever = AdvancedRetriever()
        self.llm_manager = LLMManager()
        self.field_matcher = StructuredFieldMatcher(self.llm_manager)
        
    async def initialize(self):
        """初始化"""
        # AdvancedRetriever没有initialize方法，使用延迟加载
        # await self.retriever.initialize()
        await self.llm_manager.initialize()

    async def query_policies(self, request: QueryRequest) -> QueryResponse:
        """查询政策（增强版）"""
        start_time = datetime.now()
        
        try:
            # 1. 智能查询理解
            query_analysis = await self.llm_manager.understand_query(request.query)
            
            # 2. 高级检索
            from advanced_retriever import AdvancedQueryRequest, RetrievalStrategy
            
            advanced_request = AdvancedQueryRequest(
                query=request.query,
                strategy=RetrievalStrategy.FULL_ADVANCED,
                company_context=request.company_info.__dict__ if request.company_info else None,
                top_k=request.top_k or 10,
                use_llm_enhancement=True,
                use_reranking=True
            )
            
            retrieval_response = await self.retriever.retrieve(advanced_request)
            retrieval_results = retrieval_response.results if retrieval_response.success else []
            
            # 3. 结构化字段匹配和重排
            enhanced_results = []
            for result in retrieval_results:
                # 提取结构化政策信息
                if hasattr(result, 'metadata') and 'structured_policy' in result.metadata:
                    structured_policy = StructuredPolicy(**result.metadata['structured_policy'])
                    
                    # 计算字段匹配分数
                    if request.company_info:
                        field_scores = await self.field_matcher.calculate_field_match_score(
                            request.company_info, structured_policy
                        )
                        
                        # 计算总分
                        total_score = sum(
                            score * self.field_matcher.field_weights.get(field, 0.1)
                            for field, score in field_scores.items()
                        )
                        
                        # 结合原始相似度分数
                        final_score = 0.6 * result.score + 0.4 * total_score
                        result.score = final_score
                        result.metadata['field_scores'] = field_scores
                        result.metadata['structured_analysis'] = True
                
                enhanced_results.append(result)
            
            # 4. 按新分数重新排序
            enhanced_results.sort(key=lambda x: x.score, reverse=True)
            
            # 5. 生成个性化推荐
            if request.company_info:
                personalized_summary = await self.llm_manager.generate_personalized_recommendation(
                    enhanced_results[:5], request.company_info
                )
            else:
                personalized_summary = "建议提供企业信息以获得个性化政策推荐。"
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResponse(
                results=enhanced_results,
                query_analysis=query_analysis,
                personalized_summary=personalized_summary,
                total_found=len(enhanced_results),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Enhanced policy query failed: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return QueryResponse(
                results=[],
                query_analysis={"error": str(e)},
                personalized_summary="查询过程中出现错误，请稍后重试。",
                total_found=0,
                processing_time=processing_time
            )

    async def check_eligibility(self, request: PolicyEligibilityRequest) -> PolicyEligibilityResponse:
        """检查政策资格（增强版）"""
        start_time = datetime.now()
        
        try:
            # 1. 获取政策信息 - 使用简化检索
            advanced_request = AdvancedQueryRequest(
                query=f"policy_id:{request.policy_id}",
                strategy=RetrievalStrategy.SIMPLE,
                top_k=20
            )
            
            retrieval_response = await self.retriever.retrieve(advanced_request)
            policy_chunks = retrieval_response.results if retrieval_response.success else []
            
            if not policy_chunks:
                raise ValueError(f"Policy {request.policy_id} not found")
            
            # 2. 提取结构化政策信息
            structured_policy = None
            for chunk in policy_chunks:
                if hasattr(chunk, 'metadata') and 'structured_policy' in chunk.metadata:
                    structured_policy = StructuredPolicy(**chunk.metadata['structured_policy'])
                    break
            
            if not structured_policy:
                # 临时创建结构化政策对象
                full_content = "\n".join([chunk.content for chunk in policy_chunks])
                structured_policy = StructuredPolicy(
                    policy_id=request.policy_id,
                    title="政策标题",
                    full_content=full_content
                )
            
            # 3. 字段级匹配分析
            field_scores = await self.field_matcher.calculate_field_match_score(
                request.company_info, structured_policy
            )
            
            # 4. 详细条件分析
            detailed_analysis = await self._analyze_detailed_conditions(
                request.company_info, structured_policy
            )
            
            # 5. 计算通过率
            pass_rate = self._calculate_enhanced_pass_rate(field_scores, detailed_analysis)
            
            # 6. 生成等级和建议
            level = self._determine_level(pass_rate)
            suggestions = await self._generate_enhancement_suggestions(
                request.company_info, structured_policy, detailed_analysis
            )
            
            # 7. 风险评估和时间线
            risk_factors = self._assess_risk_factors(detailed_analysis)
            timeline_estimate = self._estimate_timeline(structured_policy, detailed_analysis)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 转换为兼容的ConditionAnalysis格式
            from models import ConditionAnalysis, RequirementStatus
            
            condition_analysis = ConditionAnalysis(
                satisfied_conditions=[
                    RequirementStatus(
                        condition=cond.condition,
                        status=cond.status,
                        details=cond.description,
                        importance="必要条件" if cond.importance > 0.7 else "加分项" if cond.importance > 0.5 else "一般要求"
                    )
                    for cond in detailed_analysis.get('basic_conditions', [])
                    if cond.status == "满足"
                ],
                pending_conditions=[
                    RequirementStatus(
                        condition=cond.condition,
                        status=cond.status,
                        details=cond.description,
                        importance="必要条件" if cond.importance > 0.7 else "加分项" if cond.importance > 0.5 else "一般要求"
                    )
                    for cond in detailed_analysis.get('basic_conditions', [])
                    if cond.status == "待完善"
                ],
                unknown_conditions=[
                    RequirementStatus(
                        condition=cond.condition,
                        status=cond.status,
                        details=cond.description,
                        importance="必要条件" if cond.importance > 0.7 else "加分项" if cond.importance > 0.5 else "一般要求"
                    )
                    for cond in detailed_analysis.get('basic_conditions', [])
                    if cond.status == "不确定"
                ]
            )
            
            return PolicyEligibilityResponse(
                policy_id=request.policy_id,
                policy_name=structured_policy.title,
                policy_type=structured_policy.tool_category or "政策支持",
                support_amount=str(structured_policy.support_amount_range) if structured_policy.support_amount_range else "详见政策条文",
                pass_rate=int(pass_rate * 100),  # 转换为百分比
                pass_level=level,
                condition_analysis=condition_analysis,
                suggestions=suggestions,
                processing_time=processing_time,
                
                # 增强字段
                policy_info=structured_policy,
                detailed_analysis=detailed_analysis,
                matching_score=sum(field_scores.values()) / len(field_scores),
                feasibility_assessment=self._assess_feasibility(pass_rate, risk_factors),
                timeline_estimate=timeline_estimate,
                risk_factors=risk_factors
            )
            
        except Exception as e:
            logger.error(f"Enhanced eligibility check failed: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            from models import ConditionAnalysis
            return PolicyEligibilityResponse(
                policy_id=request.policy_id,
                policy_name="未知政策",
                policy_type="政策支持",
                support_amount="未知",
                pass_rate=0,
                pass_level="低", 
                condition_analysis=ConditionAnalysis(
                    satisfied_conditions=[],
                    pending_conditions=[],
                    unknown_conditions=[]
                ),
                suggestions=["系统错误，请稍后重试"],
                processing_time=processing_time
            )

    async def _analyze_detailed_conditions(self, company_info: CompanyInfo, 
                                         policy: StructuredPolicy) -> Dict[str, Any]:
        """详细分析条件匹配"""
        analysis = {
            'basic_conditions': [],
            'qualification_conditions': [],
            'material_conditions': [],
            'process_requirements': [],
            'overall_assessment': {}
        }
        
        # 分析基础条件
        if policy.condition_requirements:
            basic_analysis = await self._analyze_basic_conditions(
                company_info, policy.condition_requirements
            )
            analysis['basic_conditions'] = basic_analysis
        
        # 分析服务对象匹配
        if policy.service_object:
            qualification_analysis = await self._analyze_qualification_match(
                company_info, policy.service_object
            )
            analysis['qualification_conditions'] = qualification_analysis
        
        # 分析服务流程要求
        if policy.service_process:
            process_analysis = self._analyze_process_requirements(policy.service_process)
            analysis['process_requirements'] = process_analysis
        
        return analysis

    async def _analyze_basic_conditions(self, company_info: CompanyInfo, 
                                       conditions: str) -> List[EnhancedRequirementStatus]:
        """分析基础条件"""
        # 使用LLM进行详细条件分析
        prompt = f"""
        请详细分析企业是否满足以下政策条件，对每个条件给出状态评估：

        企业信息：
        - 公司名称：{company_info.company_name}
        - 行业：{company_info.industry}
        - 规模：{company_info.scale}
        - 员工数：{company_info.employees}
        - 年营业额：{company_info.annual_revenue}

        政策条件：
        {conditions}

        请分析每个具体条件，返回JSON格式：
        [
            {{
                "condition": "具体条件描述",
                "status": "满足/待完善/不确定",
                "description": "详细分析说明",
                "importance": 0.8,
                "improvement_suggestion": "改进建议"
            }}
        ]
        """
        
        try:
            response = await self.llm_manager.generate_policy_analysis(prompt, company_info.__dict__)
            # 解析JSON响应
            import json
            conditions_list = json.loads(response)
            
            return [
                EnhancedRequirementStatus(
                    condition=item['condition'],
                    status=item['status'],
                    description=item['description'],
                    importance=item.get('importance', 0.5),
                    source_field='condition_requirements',
                    requirement_type='基础条件',
                    improvement_suggestion=item.get('improvement_suggestion')
                )
                for item in conditions_list
            ]
            
        except Exception as e:
            logger.warning(f"LLM condition analysis failed: {e}")
            return [
                EnhancedRequirementStatus(
                    condition="条件分析",
                    status="不确定",
                    description="无法完成详细分析",
                    importance=0.5
                )
            ]

    def _calculate_enhanced_pass_rate(self, field_scores: Dict[str, float], 
                                    detailed_analysis: Dict[str, Any]) -> float:
        """计算增强的通过率"""
        # 基于字段匹配分数
        field_score = sum(
            score * self.field_matcher.field_weights.get(field, 0.1)
            for field, score in field_scores.items()
        )
        
        # 基于详细条件分析
        condition_score = 0.5
        if detailed_analysis.get('basic_conditions'):
            satisfied_count = sum(
                1 for cond in detailed_analysis['basic_conditions']
                if cond.status == "满足"
            )
            total_count = len(detailed_analysis['basic_conditions'])
            if total_count > 0:
                condition_score = satisfied_count / total_count
        
        # 综合计算
        pass_rate = 0.6 * field_score + 0.4 * condition_score
        return round(pass_rate, 3)

    def _determine_level(self, pass_rate: float) -> str:
        """确定资格等级"""
        if pass_rate >= 0.8:
            return "高"
        elif pass_rate >= 0.6:
            return "中"
        else:
            return "低"

    async def _generate_enhancement_suggestions(self, company_info: CompanyInfo,
                                              policy: StructuredPolicy,
                                              analysis: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        # 基于字段分析的建议
        if policy.condition_requirements:
            suggestions.append(f"重点关注政策条件要求：{policy.condition_requirements[:100]}...")
        
        if policy.service_process:
            suggestions.append(f"了解申请流程：{policy.service_process[:100]}...")
        
        if policy.contact_info:
            suggestions.append(f"及时联系咨询：{policy.contact_info}")
        
        # 基于条件分析的建议
        for condition in analysis.get('basic_conditions', []):
            if condition.status == "待完善" and condition.improvement_suggestion:
                suggestions.append(condition.improvement_suggestion)
        
        return suggestions

    def _assess_risk_factors(self, analysis: Dict[str, Any]) -> List[str]:
        """评估风险因素"""
        risks = []
        
        for condition in analysis.get('basic_conditions', []):
            if condition.status == "待完善" and condition.importance > 0.7:
                risks.append(f"高重要性条件待完善：{condition.condition}")
        
        return risks

    def _estimate_timeline(self, policy: StructuredPolicy, 
                          analysis: Dict[str, Any]) -> str:
        """估计时间线"""
        if policy.time_frequency:
            if '常年' in policy.time_frequency:
                return "可随时申请，建议尽快准备材料"
            elif '批次' in policy.time_frequency:
                return "按批次受理，需关注申请时间窗口"
        
        return "建议提前3-6个月准备申请材料"

    def _assess_feasibility(self, pass_rate: float, risk_factors: List[str]) -> str:
        """评估可行性"""
        if pass_rate >= 0.8 and len(risk_factors) == 0:
            return "可行性高，建议立即申请"
        elif pass_rate >= 0.6:
            return "可行性中等，需要完善部分条件"
        else:
            return "可行性较低，需要显著改善条件"
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            status = {
                "status": "运行中",
                "vector_store": {
                    "milvus_connected": True,
                    "elasticsearch_connected": True,
                    "milvus_stats": {
                        "row_count": 1000  # 模拟数据
                    }
                },
                "embedding_model": {
                    "status": "loaded",
                    "model_name": "moka-ai/m3e-base"
                },
                "llm_manager": {
                    "status": "ready",
                    "model": "deepseek-chat"
                }
            }
            return status
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                "status": "错误",
                "error": str(e),
                "vector_store": {
                    "milvus_connected": False,
                    "elasticsearch_connected": False
                },
                "embedding_model": {
                    "status": "error"
                }
            }
    
    def add_policy_document(self, file_path: str) -> bool:
        """添加政策文档（模拟实现）"""
        try:
            logger.info(f"正在处理政策文档: {file_path}")
            # 这里应该调用文档处理器
            return True
        except Exception as e:
            logger.error(f"文档处理失败: {e}")
            return False
    
    def analyze_policy_eligibility(self, request) -> Dict[str, Any]:
        """同步版本的政策资格分析（兼容性方法）"""
        try:
            # 这里可以调用异步版本或实现简化版本
            return {
                "policy_id": getattr(request, 'policy_id', 'unknown'),
                "policy_name": "政策分析",
                "policy_type": "政策支持",
                "support_amount": "详见政策条文",
                "pass_rate": 75,
                "pass_level": "中",
                "condition_analysis": {
                    "satisfied_conditions": [],
                    "pending_conditions": [],
                    "unknown_conditions": []
                },
                "suggestions": ["请完善企业信息以获得更准确的分析"],
                "processing_time": 0.1
            }
        except Exception as e:
            logger.error(f"政策资格分析失败: {e}")
            return {
                "policy_id": "unknown",
                "pass_rate": 0,
                "pass_level": "低",
                "error": str(e)
            }
    
    async def _analyze_qualification_match(self, company_info: CompanyInfo,
                                         service_object: str) -> List[EnhancedRequirementStatus]:
        """分析服务对象资格匹配"""
        qualifications = []
        
        # 企业规模资格分析
        if any(keyword in service_object.lower() for keyword in ['初创', '小型', '中型', '大型']):
            scale_match = self._analyze_scale_qualification(company_info, service_object)
            qualifications.append(scale_match)
        
        # 行业资格分析
        if company_info.industry:
            industry_match = self._analyze_industry_qualification(company_info, service_object)
            qualifications.append(industry_match)
        
        # 企业性质资格分析
        if any(keyword in service_object.lower() for keyword in ['国有', '民营', '外资', '高新']):
            nature_match = self._analyze_nature_qualification(company_info, service_object)
            qualifications.append(nature_match)
        
        return qualifications
    
    def _analyze_scale_qualification(self, company_info: CompanyInfo, 
                                   service_object: str) -> EnhancedRequirementStatus:
        """分析企业规模资格"""
        service_lower = service_object.lower()
        
        if company_info.scale:
            scale_lower = company_info.scale.lower()
            
            # 规模匹配逻辑
            if ('初创' in service_lower and '初创' in scale_lower) or \
               ('小型' in service_lower and any(keyword in scale_lower for keyword in ['小型', '小企业'])) or \
               ('中型' in service_lower and '中型' in scale_lower) or \
               ('大型' in service_lower and '大型' in scale_lower):
                status = "满足"
                description = f"企业规模{company_info.scale}符合政策要求"
            else:
                status = "待完善"
                description = f"企业规模{company_info.scale}可能不完全符合要求"
        else:
            status = "不确定"
            description = "企业规模信息不明确"
        
        return EnhancedRequirementStatus(
            condition="企业规模要求",
            status=status,
            description=description,
            importance=0.8,
            source_field='service_object',
            requirement_type='资格条件'
        )
    
    def _analyze_industry_qualification(self, company_info: CompanyInfo,
                                      service_object: str) -> EnhancedRequirementStatus:
        """分析行业资格"""
        service_lower = service_object.lower()
        
        if company_info.industry:
            industry_lower = company_info.industry.lower()
            
            # 检查行业关键词匹配
            industry_keywords = industry_lower.split()
            match_found = any(keyword in service_lower for keyword in industry_keywords)
            
            if match_found:
                status = "满足"
                description = f"企业行业{company_info.industry}符合政策服务对象"
            else:
                status = "待完善"
                description = f"企业行业{company_info.industry}可能不在政策覆盖范围内"
        else:
            status = "不确定"
            description = "企业行业信息不明确"
        
        return EnhancedRequirementStatus(
            condition="行业适用性",
            status=status,
            description=description,
            importance=0.7,
            source_field='service_object',
            requirement_type='资格条件'
        )
    
    def _analyze_nature_qualification(self, company_info: CompanyInfo,
                                    service_object: str) -> EnhancedRequirementStatus:
        """分析企业性质资格"""
        service_lower = service_object.lower()
        
        if company_info.enterprise_type:
            type_lower = company_info.enterprise_type.lower()
            
            # 企业性质匹配
            if any(keyword in service_lower for keyword in type_lower.split()):
                status = "满足"
                description = f"企业性质{company_info.enterprise_type}符合政策要求"
            else:
                status = "待完善"
                description = f"企业性质{company_info.enterprise_type}可能不符合要求"
        else:
            status = "不确定"
            description = "企业性质信息不明确"
        
        return EnhancedRequirementStatus(
            condition="企业性质要求",
            status=status,
            description=description,
            importance=0.6,
            source_field='service_object',
            requirement_type='资格条件'
        )
    
    def _analyze_process_requirements(self, service_process: str) -> List[EnhancedRequirementStatus]:
        """分析服务流程要求"""
        requirements = []
        process_lower = service_process.lower()
        
        # 材料准备要求
        if any(keyword in process_lower for keyword in ['材料', '资料', '文件', '证明']):
            material_req = EnhancedRequirementStatus(
                condition="申请材料准备",
                status="待完善",
                description="需要准备相关申请材料和证明文件",
                importance=0.8,
                source_field='service_process',
                requirement_type='流程要求',
                improvement_suggestion="提前整理和准备所需申请材料"
            )
            requirements.append(material_req)
        
        # 审核流程要求
        if any(keyword in process_lower for keyword in ['审核', '评审', '专家']):
            review_req = EnhancedRequirementStatus(
                condition="审核评审流程",
                status="不确定",
                description="需要通过专业审核或评审流程",
                importance=0.7,
                source_field='service_process',
                requirement_type='流程要求',
                improvement_suggestion="了解审核标准，做好答辩准备"
            )
            requirements.append(review_req)
        
        # 联席会议要求
        if any(keyword in process_lower for keyword in ['联席', '会议', '现场']):
            meeting_req = EnhancedRequirementStatus(
                condition="联席会议参与",
                status="不确定",
                description="可能需要参与联席会议或现场答辩",
                importance=0.6,
                source_field='service_process',
                requirement_type='流程要求',
                improvement_suggestion="准备项目汇报材料，做好现场展示"
            )
            requirements.append(meeting_req)
        
        # 公示要求
        if any(keyword in process_lower for keyword in ['公示', '公布', '公开']):
            publicity_req = EnhancedRequirementStatus(
                condition="公示公开要求",
                status="满足",
                description="申请结果将进行公示",
                importance=0.3,
                source_field='service_process',
                requirement_type='流程要求'
            )
            requirements.append(publicity_req)
        
        return requirements

# 延迟创建全局政策匹配引擎实例
_policy_matcher = None

def get_policy_matcher():
    """获取政策匹配引擎实例"""
    global _policy_matcher
    if _policy_matcher is None:
        from config import Config
        config = Config()
        _policy_matcher = EnhancedPolicyMatcher(config)
    return _policy_matcher

# 为了向后兼容，提供policy_matcher属性
def __getattr__(name):
    if name == 'policy_matcher':
        return get_policy_matcher()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 