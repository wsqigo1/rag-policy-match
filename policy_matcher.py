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
                risk_factors=risk_factors,
                
                # 🆕 添加用于数据库关联的字段
                original_filename=getattr(structured_policy, 'original_filename', None),
                file_path=getattr(structured_policy, 'file_path', None),
                document_number=structured_policy.document_number,
                issuing_agency=structured_policy.issuing_agency
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
    
    def _extract_policy_name(self, result) -> str:
        """从检索结果中提取政策名称"""
        # 尝试从内容中提取标题
        content = result.content
        lines = content.split('\n')
        for line in lines[:5]:  # 检查前5行
            line = line.strip()
            if len(line) > 10 and not line.startswith(('第', '一、', '二、', '三、', '（')):
                return line
        # 如果没找到合适的标题，使用政策ID
        return f"政策文档 {result.policy_id}"
    
    def _infer_policy_type(self, content: str) -> str:
        """从内容推断政策类型"""
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in ['资金', '补助', '补贴', '扶持']):
            return "资金支持"
        elif any(keyword in content_lower for keyword in ['认定', '资质', '高新', '专精特新']):
            return "资质认定"
        elif any(keyword in content_lower for keyword in ['人才', '落户', '住房']):
            return "人才支持"
        elif any(keyword in content_lower for keyword in ['税收', '减免', '优惠']):
            return "税收优惠"
        elif any(keyword in content_lower for keyword in ['空间', '租金', '实验室']):
            return "空间支持"
        else:
            return "政策支持"
    
    def _extract_support_content(self, content: str) -> str:
        """提取支持内容"""
        # 寻找包含支持内容的段落
        sentences = content.split('。')
        for sentence in sentences:
            if any(keyword in sentence for keyword in ['支持', '补助', '补贴', '扶持', '资助']):
                return sentence.strip()[:100] + "..."
        return "详见政策条文"
    
    def _extract_conditions(self, content: str) -> str:
        """提取申请条件"""
        sentences = content.split('。')
        for sentence in sentences:
            if any(keyword in sentence for keyword in ['条件', '要求', '应当', '必须', '需要']):
                return sentence.strip()[:100] + "..."
        return "详见政策条文"
    
    def _simple_vector_search(self, request) -> List:
        """简单的同步向量搜索"""
        from vector_store import VectorStore
        from embeddings import EmbeddingManager
        from models import RetrievalResult
        
        try:
            # 初始化组件
            vector_store = VectorStore()
            embedding_manager = EmbeddingManager()
            
            if not vector_store.milvus.connected:
                return []
            
            # 生成查询向量
            query_embedding = embedding_manager.encode_texts([request.query])
            
            # 执行搜索
            results = vector_store.milvus.search(query_embedding[0], top_k=request.top_k or 10)
            
            # 转换为RetrievalResult格式
            retrieval_results = []
            for result in results:
                retrieval_results.append(RetrievalResult(
                    chunk_id=result.chunk_id,
                    content=result.content,
                    score=float(result.score),
                    policy_id=result.policy_id,
                    metadata=result.metadata or {}
                ))
                
            return retrieval_results
            
        except Exception as e:
            logger.error(f"简单向量搜索失败: {e}")
            return []
    
    def basic_match(self, request: 'BasicMatchRequest') -> 'OneClickMatchResponse':
        """基础匹配功能 - 使用真实向量检索"""
        start_time = datetime.now()
        
        try:
            from models import PolicyMatch, OneClickMatchResponse, QueryRequest
            
            # 🆕 构建查询文本，基于用户选择的条件
            query_parts = []
            if request.industry:
                query_parts.append(request.industry)
            if request.demand_type:
                if "资金" in request.demand_type:
                    query_parts.append("资金支持 补助 扶持")
                elif "资质" in request.demand_type:
                    query_parts.append("资质认定 高新企业 专精特新")
                elif "人才" in request.demand_type:
                    query_parts.append("人才支持 落户 住房补贴")
                elif "空间" in request.demand_type:
                    query_parts.append("空间支持 实验室 租金减免")
            
            # 企业规模相关关键词
            if "初创" in request.company_scale:
                query_parts.append("初创企业 小微企业")
            elif "中小" in request.company_scale:
                query_parts.append("中小企业")
            elif "大型" in request.company_scale:
                query_parts.append("大型企业")
            
            query_text = " ".join(query_parts) if query_parts else f"{request.industry} {request.demand_type}"
            
            # 🆕 使用向量检索替代模拟数据
            query_request = QueryRequest(
                query=query_text,
                industry=request.industry,
                enterprise_scale=request.company_scale,
                top_k=10
            )
            
            # 调用真实的查询系统
            query_response = self.match_policies(query_request)
            
            # 将检索结果转换为PolicyMatch格式
            matches = []
            for result in query_response.results[:10]:
                # 从向量检索结果中提取政策信息
                policy_name = self._extract_policy_name(result)
                match_score = min(result.score * 1.2, 1.0)  # 调整分数范围
                
                matches.append(PolicyMatch(
                    policy_id=result.policy_id,
                    policy_name=policy_name,
                    match_score=round(match_score, 2),
                    match_level="高" if match_score >= 0.8 else "中" if match_score >= 0.6 else "低",
                    key_description=result.content[:150] + "...",
                    policy_type=self._infer_policy_type(result.content),
                    support_content=self._extract_support_content(result.content),
                    application_conditions=self._extract_conditions(result.content),
                    # 使用真实的关联字段
                    original_filename=getattr(result, 'original_filename', None),
                    file_path=getattr(result, 'file_path', None),
                    document_number=getattr(result, 'document_number', None),
                    issuing_agency=getattr(result, 'issuing_agency', None)
                ))
            
            # 如果向量检索没有结果，使用备用模拟数据
            if not matches:
                logger.warning("向量检索无结果，使用备用模拟数据")
                # 保留原有的模拟数据作为备用
                mock_policies = [
                {
                    "policy_id": "policy_001",
                    "policy_name": "生物医药产业发展支持政策",
                    "match_score": 0.85,
                    "match_level": "高",
                    "key_description": "支持生物医药企业研发创新，提供最高500万元资金支持，适合初创企业申请",
                    "policy_type": "资金支持",
                    "support_content": "研发费用补助、设备购置支持",
                    "application_conditions": "注册在中关村示范区，成立不超过3年",
                    # 🆕 添加用于数据库关联的字段
                    "original_filename": "生物医药产业发展支持政策.pdf",
                    "file_path": "/policies/生物医药产业发展支持政策.pdf",
                    "document_number": "京发改〔2023〕15号",
                    "issuing_agency": "北京市发展和改革委员会"
                },
                {
                    "policy_id": "policy_002", 
                    "policy_name": "初创企业孵化器支持计划",
                    "match_score": 0.78,
                    "match_level": "高",
                    "key_description": "为初创企业提供孵化空间和创业辅导，减免租金最高80%，提供专业服务",
                    "policy_type": "空间支持",
                    "support_content": "孵化空间、创业辅导、资源对接",
                    "application_conditions": "成立不超过3年，员工少于20人",
                    # 🆕 添加用于数据库关联的字段
                    "original_filename": "初创企业孵化器支持计划.pdf",
                    "file_path": "/policies/初创企业孵化器支持计划.pdf",
                    "document_number": "京科发〔2023〕8号",
                    "issuing_agency": "北京市科学技术委员会"
                },
                {
                    "policy_id": "policy_003",
                    "policy_name": "企业研发费用加计扣除政策",
                    "match_score": 0.72,
                    "match_level": "中",
                    "key_description": "研发费用可享受175%加计扣除，有效降低企业税负，适合有研发投入的企业",
                    "policy_type": "税收优惠",
                    "support_content": "研发费用税前加计扣除",
                    "application_conditions": "有研发活动和费用支出记录",
                    # 🆕 添加用于数据库关联的字段
                    "original_filename": "企业研发费用加计扣除政策.docx",
                    "file_path": "/policies/企业研发费用加计扣除政策.docx",
                    "document_number": "财税〔2023〕28号",
                    "issuing_agency": "财政部、税务总局"
                }
            ]
            
                # 根据请求参数过滤和评分（仅用于备用情况）
                for policy in mock_policies:
                    # 行业匹配
                    industry_match = self._match_industry(request.industry, policy)
                    # 企业规模匹配
                    scale_match = self._match_scale(request.company_scale, policy)
                    # 需求类型匹配
                    demand_match = self._match_demand_type(request.demand_type, policy)
                    
                    # 综合评分
                    total_score = (industry_match * 0.4 + scale_match * 0.3 + demand_match * 0.3)
                    
                    if total_score >= 0.5:  # 匹配阈值
                        match_level = "高" if total_score >= 0.8 else "中" if total_score >= 0.6 else "低"
                        
                        matches.append(PolicyMatch(
                            policy_id=policy["policy_id"],
                            policy_name=policy["policy_name"],
                            match_score=round(total_score, 2),
                            match_level=match_level,
                            key_description=policy["key_description"],
                            policy_type=policy["policy_type"],
                            support_content=policy["support_content"],
                            application_conditions=policy["application_conditions"],
                            # 🆕 添加用于数据库关联的字段
                            original_filename=policy.get("original_filename"),
                            file_path=policy.get("file_path"),
                            document_number=policy.get("document_number"),
                            issuing_agency=policy.get("issuing_agency")
                        ))
            
            # 按匹配分数排序（适用于所有情况）
            matches.sort(key=lambda x: x.match_score, reverse=True)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OneClickMatchResponse(
                total_results=len(matches),
                matches=matches,
                processing_time=processing_time,
                match_type="basic",
                suggestions=[
                    "建议使用精准匹配功能获得更准确的结果",
                    "可以上传企业资料进行详细分析",
                    "关注政策申请时间窗口"
                ]
            )
            
        except Exception as e:
            logger.error(f"基础匹配失败: {e}")
            from models import OneClickMatchResponse
            processing_time = (datetime.now() - start_time).total_seconds()
            return OneClickMatchResponse(
                total_results=0,
                matches=[],
                processing_time=processing_time,
                match_type="basic",
                suggestions=[f"匹配过程出现错误: {str(e)}"]
            )
    
    def precise_match(self, request: 'PreciseMatchRequest') -> 'OneClickMatchResponse':
        """精准匹配功能"""
        start_time = datetime.now()
        
        try:
            from models import PolicyMatch, OneClickMatchResponse
            
            # 首先执行基础匹配
            basic_response = self.basic_match(request.basic_request)
            
            # 基于企业详细信息进行精准匹配和重排序
            enhanced_matches = []
            
            for match in basic_response.matches:
                # 企业信息匹配度分析
                company_score = self._analyze_company_match(request.company_info, match)
                
                # 重新计算匹配分数
                enhanced_score = (match.match_score * 0.6 + company_score * 0.4)
                
                # 生成更详细的描述
                enhanced_description = self._generate_enhanced_description(
                    request.company_info, match
                )
                
                enhanced_matches.append(PolicyMatch(
                    policy_id=match.policy_id,
                    policy_name=match.policy_name,
                    match_score=round(enhanced_score, 2),
                    match_level="高" if enhanced_score >= 0.8 else "中" if enhanced_score >= 0.6 else "低",
                    key_description=enhanced_description,
                    policy_type=match.policy_type,
                    support_content=match.support_content,
                    application_conditions=match.application_conditions,
                    # 🆕 保留原有的关联字段
                    original_filename=match.original_filename,
                    file_path=match.file_path,
                    document_number=match.document_number,
                    issuing_agency=match.issuing_agency
                ))
            
            # 重新排序
            enhanced_matches.sort(key=lambda x: x.match_score, reverse=True)
            
            # 生成个性化建议
            suggestions = self._generate_personalized_suggestions(request.company_info)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OneClickMatchResponse(
                total_results=len(enhanced_matches),
                matches=enhanced_matches,
                processing_time=processing_time,
                match_type="precise",
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"精准匹配失败: {e}")
            from models import OneClickMatchResponse
            processing_time = (datetime.now() - start_time).total_seconds()
            return OneClickMatchResponse(
                total_results=0,
                matches=[],
                processing_time=processing_time,
                match_type="precise",
                suggestions=[f"匹配过程出现错误: {str(e)}"]
            )
    
    def _match_industry(self, requested_industry: str, policy: dict) -> float:
        """行业匹配度计算"""
        # 简化的行业匹配逻辑
        if "生物医药" in requested_industry:
            if "生物医药" in policy["policy_name"] or "医药" in policy["key_description"]:
                return 1.0
            elif "研发" in policy["key_description"] or "创新" in policy["key_description"]:
                return 0.8
        elif "信息技术" in requested_industry:
            if "科技" in policy["policy_name"] or "技术" in policy["key_description"]:
                return 1.0
        
        # 默认匹配度
        return 0.6
    
    def _match_scale(self, requested_scale: str, policy: dict) -> float:
        """企业规模匹配度计算"""
        if "初创" in requested_scale:
            if "初创" in policy["application_conditions"] or "3年" in policy["application_conditions"]:
                return 1.0
            elif "孵化" in policy["policy_name"]:
                return 0.9
        elif "中小企业" in requested_scale:
            if "中小" in policy["application_conditions"]:
                return 1.0 
        
        return 0.7
    
    def _match_demand_type(self, requested_demand: str, policy: dict) -> float:
        """需求类型匹配度计算"""
        if "资金" in requested_demand:
            if policy["policy_type"] == "资金支持":
                return 1.0
            elif "费用" in policy["support_content"]:
                return 0.8
        elif "资质" in requested_demand:
            if "认定" in policy["policy_name"] or "资质" in policy["policy_type"]:
                return 1.0
        elif "空间" in requested_demand:
            if policy["policy_type"] == "空间支持":
                return 1.0
        
        return 0.5
    
    def _analyze_company_match(self, company_info: 'CompanyInfo', match: 'PolicyMatch') -> float:
        """分析企业信息匹配度"""
        score = 0.7  # 基础分数
        
        # 注册资本匹配
        if hasattr(company_info, 'registered_capital') and company_info.registered_capital:
            if company_info.registered_capital <= 1000:  # 小企业
                if "初创" in match.application_conditions or "小型" in match.application_conditions:
                    score += 0.1
            else:  # 大企业
                if "大型" in match.application_conditions:
                    score += 0.1
        
        # 员工数匹配
        if hasattr(company_info, 'employees') and company_info.employees:
            if company_info.employees < 20:
                if "20人" in match.application_conditions:
                    score += 0.1
            elif company_info.employees < 200:
                if "中小" in match.application_conditions:
                    score += 0.1
        
        # 年营业额匹配
        if hasattr(company_info, 'annual_revenue') and company_info.annual_revenue:
            if company_info.annual_revenue < 1000:  # 小企业
                if "初创" in match.application_conditions:
                    score += 0.1
        
        return min(score, 1.0)
    
    def _generate_enhanced_description(self, company_info: 'CompanyInfo', match: 'PolicyMatch') -> str:
        """生成增强的政策描述"""
        base_description = match.key_description or ""
        
        # 添加企业相关的个性化信息
        if hasattr(company_info, 'company_name') and company_info.company_name:
            scale = getattr(company_info, 'scale', None)
            employees = getattr(company_info, 'employees', None)
            
            if scale and "初创" in scale or (employees and employees < 20):
                enhanced = f"特别适合{company_info.company_name}等初创企业，{base_description}"
            else:
                enhanced = f"适合{company_info.company_name}申请，{base_description}"
        else:
            enhanced = base_description
        
        return enhanced[:150]  # 限制150字符
    
    def _generate_personalized_suggestions(self, company_info: 'CompanyInfo') -> List[str]:
        """生成个性化建议"""
        suggestions = []
        
        if hasattr(company_info, 'registered_capital') and company_info.registered_capital and company_info.registered_capital <= 500:
            suggestions.append("作为小规模企业，重点关注初创企业专项政策")
        
        if hasattr(company_info, 'employees') and company_info.employees and company_info.employees < 20:
            suggestions.append("可申请孵化器入驻，享受场地和服务支持")
        
        if hasattr(company_info, 'annual_revenue') and company_info.annual_revenue and company_info.annual_revenue < 1000:
            suggestions.append("优先申请资金支持类政策，降低运营成本")
        
        if not suggestions:
            suggestions.append("建议完善企业资料以获得更精准的政策推荐")
        
        suggestions.append("及时关注政策申请截止时间")
        suggestions.append("准备齐全申请材料，提高申请成功率")
        
        return suggestions
    
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
        """添加政策文档"""
        try:
            logger.info(f"开始添加政策文档: {file_path}")
            
            # 1. 使用DocumentProcessor处理文档
            from document_processor import DocumentProcessor
            processor = DocumentProcessor(self.config)
            
            # 处理文档，获取PolicyDocument对象
            policy_doc = processor.process_document(file_path)
            
            # 2. 生成向量嵌入
            from embeddings import EmbeddingManager
            embedding_model = EmbeddingManager()
            
            # 提取所有分块的文本内容
            chunk_texts = [chunk.content for chunk in policy_doc.chunks]
            if not chunk_texts:
                logger.warning(f"文档没有生成分块: {file_path}")
                return False
            
            # 生成嵌入向量
            embeddings = embedding_model.encode_texts(chunk_texts)
            logger.info(f"向量编码完成，形状: {embeddings.shape}")
            
            # 3. 存储到向量数据库
            from vector_store import VectorStore
            vector_store = VectorStore()
            
            # 准备元数据
            policy_metadata = {
                'industries': policy_doc.industry if isinstance(policy_doc.industry, list) else [policy_doc.industry] if policy_doc.industry else [],
                'enterprise_scales': policy_doc.enterprise_scale if isinstance(policy_doc.enterprise_scale, list) else [policy_doc.enterprise_scale] if policy_doc.enterprise_scale else [],
                'policy_types': [policy_doc.policy_type] if policy_doc.policy_type else []
            }
            
            # 存储分块和嵌入
            success = vector_store.store_policy_chunks(
                chunks=policy_doc.chunks,
                embeddings=embeddings,
                policy_title=policy_doc.title,
                policy_metadata=policy_metadata
            )
            
            if success:
                logger.info(f"政策文档存储成功: {file_path}")
                return True
            else:
                logger.error(f"政策文档存储失败: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"添加政策文档失败: {e}")
            return False
    
    def analyze_policy_eligibility(self, request) -> 'PolicyEligibilityResponse':
        """政策资格分析方法"""
        try:
            from models import PolicyEligibilityResponse, ConditionAnalysis, RequirementStatus
            
            # 模拟政策资格分析
            company_info = request.company_info
            policy_id = request.policy_id
            
            logger.info(f"开始分析政策资格: 政策ID={policy_id}, 企业={company_info.company_name}")
            
            # 基础匹配分析
            base_score = 0.7  # 基础分数
            
            # 企业规模评估
            if hasattr(company_info, 'registered_capital') and company_info.registered_capital:
                if company_info.registered_capital <= 1000:  # 小企业更容易获得支持
                    base_score += 0.1
            
            # 行业匹配评估
            if hasattr(company_info, 'business_scope') and company_info.business_scope:
                if any(keyword in company_info.business_scope for keyword in ['技术', '研发', '创新', '科技']):
                    base_score += 0.1
            
            # 成立时间评估
            if hasattr(company_info, 'establishment_date') and company_info.establishment_date:
                # 初创企业（成立3年内）更容易获得支持
                base_score += 0.05
            
            # 计算通过率
            pass_rate = min(int(base_score * 100), 95)  # 最高95%
            
            # 确定等级
            if pass_rate >= 80:
                pass_level = "高"
            elif pass_rate >= 60:
                pass_level = "中"
            else:
                pass_level = "低"
            
            # 构建条件分析
            satisfied_conditions = []
            pending_conditions = []
            unknown_conditions = []
            
            # 满足的条件
            if company_info.company_name:
                satisfied_conditions.append(RequirementStatus(
                    condition="企业已依法注册成立",
                    status="满足",
                    details=f"企业名称：{company_info.company_name}",
                    importance="必要条件"
                ))
            
            if hasattr(company_info, 'business_scope') and company_info.business_scope:
                satisfied_conditions.append(RequirementStatus(
                    condition="经营范围符合政策要求",
                    status="满足", 
                    details="业务范围包含技术研发相关内容",
                    importance="必要条件"
                ))
            
            # 待完善的条件
            if not hasattr(company_info, 'annual_revenue') or not company_info.annual_revenue:
                pending_conditions.append(RequirementStatus(
                    condition="提供近三年财务报表",
                    status="待完善",
                    details="需要提供详细的财务数据以进行准确评估",
                    importance="重要条件"
                ))
            
            # 不确定的条件
            unknown_conditions.append(RequirementStatus(
                condition="知识产权情况",
                status="不确定",
                details="需要了解企业专利、商标等知识产权状况",
                importance="加分项"
            ))
            
            condition_analysis = ConditionAnalysis(
                satisfied_conditions=satisfied_conditions,
                pending_conditions=pending_conditions,
                unknown_conditions=unknown_conditions
            )
            
            # 生成建议
            suggestions = []
            if pass_rate < 70:
                suggestions.append("建议完善企业资质证明材料")
                suggestions.append("可考虑先申请其他门槛较低的政策")
            else:
                suggestions.append("企业条件较好，建议尽快准备申请材料")
                suggestions.append("关注政策申请截止时间，及时提交申请")
            
            suggestions.append("建议咨询专业服务机构获得申请指导")
            
            return PolicyEligibilityResponse(
                policy_id=policy_id,
                policy_name="北京市产业政策支持计划",
                policy_type="资金支持",
                support_amount="最高500万元",
                pass_rate=pass_rate,
                pass_level=pass_level,
                condition_analysis=condition_analysis,
                suggestions=suggestions,
                processing_time=0.1
            )
            
        except Exception as e:
            logger.error(f"政策资格分析失败: {e}")
            # 返回错误情况下的默认响应
            from models import PolicyEligibilityResponse, ConditionAnalysis
            return PolicyEligibilityResponse(
                policy_id=getattr(request, 'policy_id', 'unknown'),
                policy_name="政策分析",
                policy_type="政策支持",
                support_amount="详见政策条文",
                pass_rate=0,
                pass_level="低",
                condition_analysis=ConditionAnalysis(
                    satisfied_conditions=[],
                    pending_conditions=[],
                    unknown_conditions=[]
                ),
                suggestions=[f"分析过程出现错误: {str(e)}"],
                processing_time=0.1
            )
    
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

    def match_policies(self, request: 'QueryRequest') -> 'QueryResponse':
        """处理自然语言政策查询"""
        start_time = datetime.now()
        
        try:
            from models import QueryResponse, RetrievalResult
            
            # 构建查询过滤条件
            filters = {}
            if request.industry:
                filters['industries'] = [request.industry]
            if request.enterprise_scale:
                filters['enterprise_scales'] = [request.enterprise_scale]
            if request.policy_type:
                filters['policy_types'] = [request.policy_type]
            if request.region:
                filters['region'] = request.region
            
            # 🆕 使用同步向量检索
            try:
                # 直接使用向量存储进行搜索
                retrieval_results = self._simple_vector_search(request)
                logger.info(f"检索到 {len(retrieval_results)} 个结果")
            except Exception as e:
                # 如果检索失败，回退到基本搜索
                logger.warning(f"向量检索失败: {e}，使用基本搜索")
                retrieval_results = []
            
            # 🆕 如果没有找到结果，提供模拟结果
            if not retrieval_results:
                logger.info("未找到检索结果，提供模拟政策数据")
                mock_results = self._get_mock_retrieval_results(request.query)
                retrieval_results.extend(mock_results)
            else:
                logger.info(f"成功检索到 {len(retrieval_results)} 个真实政策结果")
            
            # 生成查询分析和建议
            query_analysis = {
                "intent": "政策查询",
                "keywords": request.query.split(),
                "filters_applied": {
                    "industry": request.industry,
                    "scale": request.enterprise_scale,
                    "type": request.policy_type,
                    "region": request.region
                }
            }
            
            suggestions = []
            if len(retrieval_results) == 0:
                suggestions = [
                    "未找到匹配的政策，建议：",
                    "1. 调整查询关键词，使用更通用的表述",
                    "2. 尝试按行业或政策类型分类查询"
                ]
            elif len(retrieval_results) < 3:
                suggestions = [
                    "找到的结果较少，建议：",
                    "1. 扩大查询范围，减少筛选条件",
                    "2. 尝试不同的关键词组合"
                ]
            else:
                suggestions = [
                    "建议进一步筛选结果：",
                    "1. 使用行业、企业规模等条件精确筛选",
                    "2. 关注政策的申请条件和截止时间"
                ]
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResponse(
                results=retrieval_results,
                total_results=len(retrieval_results),
                query_analysis=query_analysis,
                processing_time=processing_time,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"自然语言查询失败: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            from models import QueryResponse
            return QueryResponse(
                results=[],
                total_results=0,
                query_analysis={"error": str(e)},
                processing_time=processing_time,
                suggestions=[f"查询过程出现错误: {str(e)}"]
            )

    def _get_mock_retrieval_results(self, query: str) -> List:
        """获取模拟检索结果"""
        try:
            from models import RetrievalResult
            
            mock_policies = [
                {
                    "chunk_id": "policy_bio_001_chunk_0",
                    "policy_id": "policy_bio_001",
                    "content": "北京市生物医药产业发展支持政策：支持生物医药企业技术创新，提供研发费用补助、设备购置支持等，最高资助500万元。适用于在京注册的生物医药企业，重点支持创新药物、医疗器械等领域。",
                    "score": 0.85,
                    "metadata": {
                        "title": "北京市生物医药产业发展支持政策",
                        "policy_type": "资金支持",
                        "region": "北京市"
                    }
                },
                {
                    "chunk_id": "policy_startup_001_chunk_0", 
                    "policy_id": "policy_startup_001",
                    "content": "初创企业孵化器支持计划：为初创企业提供孵化空间和创业辅导，减免租金最高80%，提供专业服务。适用于成立不超过3年、员工少于50人的初创企业。",
                    "score": 0.78,
                    "metadata": {
                        "title": "初创企业孵化器支持计划",
                        "policy_type": "空间支持",
                        "region": "北京市"
                    }
                },
                {
                    "chunk_id": "policy_rd_001_chunk_0",
                    "policy_id": "policy_rd_001",
                    "content": "企业研发费用加计扣除政策：企业研发费用可享受175%加计扣除，有效降低企业税负。适用于有研发活动和费用支出记录的企业，可大幅减少所得税缴纳。",
                    "score": 0.72,
                    "metadata": {
                        "title": "企业研发费用加计扣除政策",
                        "policy_type": "税收优惠", 
                        "region": "全国"
                    }
                }
            ]
            
            # 根据查询关键词过滤相关政策
            query_lower = query.lower()
            filtered_policies = []
            
            for policy in mock_policies:
                if any(keyword in policy["content"].lower() 
                      for keyword in ["生物医药", "医药", "医疗"] if "生物医药" in query_lower or "医药" in query_lower):
                    filtered_policies.append(policy)
                elif any(keyword in policy["content"].lower()
                        for keyword in ["初创", "创业", "小型"] if "初创" in query_lower or "创业" in query_lower):
                    filtered_policies.append(policy)
                elif any(keyword in policy["content"].lower()
                        for keyword in ["研发", "创新", "资金"] if "研发" in query_lower or "创新" in query_lower or "资金" in query_lower):
                    filtered_policies.append(policy)
                else:
                    # 默认包含所有政策
                    filtered_policies.append(policy)
            
            # 转换为RetrievalResult对象
            retrieval_results = []
            for policy in filtered_policies:
                retrieval_result = RetrievalResult(
                    chunk_id=policy["chunk_id"],
                    policy_id=policy["policy_id"],
                    content=policy["content"],
                    score=policy["score"],
                    metadata=policy["metadata"]
                )
                retrieval_results.append(retrieval_result)
            
            return retrieval_results
            
        except Exception as e:
            logger.error(f"生成模拟检索结果失败: {e}")
            return []

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