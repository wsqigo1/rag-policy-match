from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
import tempfile
from pathlib import Path

from models import (
    QueryRequest, QueryResponse, SystemStatus,
    BasicMatchRequest, PreciseMatchRequest, OneClickMatchResponse,
    PolicyEligibilityRequest, PolicyEligibilityResponse,
    CompanyDevelopmentDataRequest, MajorEnterpriseDataRequest
)
from policy_matcher import policy_matcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_policy_matcher():
    """获取policy_matcher实例"""
    return policy_matcher

# 创建FastAPI应用
app = FastAPI(
    title="政策匹配检索系统",
    description="基于RAG的政策文档智能匹配系统，支持自然语言查询和一键匹配",
    version="2.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "政策匹配检索系统API",
        "version": "2.0.0",
        "status": "运行中",
        "features": {
            "natural_language_query": "支持自然语言政策查询",
            "basic_match": "支持三选项基础匹配",
            "precise_match": "支持基于企业信息的精准匹配",
            "eligibility_analysis": "支持政策申请通过率自测分析"
        }
    }

# ======= 自然语言查询接口 =======

@app.post("/search", response_model=QueryResponse)
async def search_policies(query_request: QueryRequest):
    """
    自然语言政策搜索接口
    
    Args:
        query_request: 查询请求对象
        
    Returns:
        查询响应结果
    """
    try:
        logger.info(f"收到自然语言查询请求: {query_request.query}")
        
        # 执行政策匹配
        policy_matcher = get_policy_matcher()
        response = policy_matcher.match_policies(query_request)
        
        logger.info(f"自然语言查询完成，返回 {response.total_results} 个结果")
        return response
        
    except Exception as e:
        logger.error(f"自然语言查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@app.get("/search/quick")
async def quick_search(
    q: str,
    industry: str = None,
    enterprise_scale: str = None,
    policy_type: str = None,
    region: str = None,
    top_k: int = 10
):
    """
    快速查询接口（GET方式）
    
    Args:
        q: 查询文本
        industry: 行业筛选
        enterprise_scale: 企业规模
        policy_type: 政策类型
        region: 地区
        top_k: 返回结果数量
        
    Returns:
        查询结果
    """
    try:
        query_request = QueryRequest(
            query=q,
            industry=industry,
            enterprise_scale=enterprise_scale,
            policy_type=policy_type,
            region=region,
            top_k=min(top_k, 50)  # 限制最大数量
        )
        
        policy_matcher = get_policy_matcher()
        response = policy_matcher.match_policies(query_request)
        return response
        
    except Exception as e:
        logger.error(f"快速查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

# ======= 一键匹配接口 =======

@app.post("/basic-match", response_model=OneClickMatchResponse)
async def basic_match(request: BasicMatchRequest):
    """
    基础三选项匹配接口
    
    Args:
        request: 基础匹配请求
        
    Returns:
        一键匹配响应
    """
    try:
        logger.info(f"收到基础匹配请求: 行业={request.industry}, 规模={request.company_scale}, 需求={request.demand_type}")
        
        # 执行基础匹配
        policy_matcher = get_policy_matcher()
        response = policy_matcher.basic_match(request)
        
        logger.info(f"基础匹配完成，返回 {response.total_results} 个结果")
        return response
        
    except Exception as e:
        logger.error(f"基础匹配失败: {e}")
        raise HTTPException(status_code=500, detail=f"基础匹配失败: {str(e)}")

@app.post("/precise-match", response_model=OneClickMatchResponse)
async def precise_match(request: PreciseMatchRequest):
    """
    精准匹配接口（基于企业详细信息）
    
    Args:
        request: 精准匹配请求
        
    Returns:
        一键匹配响应
    """
    try:
        logger.info(f"收到精准匹配请求: 企业={request.company_info.company_name}")
        
        # 执行精准匹配
        policy_matcher = get_policy_matcher()
        response = policy_matcher.precise_match(request)
        
        logger.info(f"精准匹配完成，返回 {response.total_results} 个结果")
        return response
        
    except Exception as e:
        logger.error(f"精准匹配失败: {e}")
        raise HTTPException(status_code=500, detail=f"精准匹配失败: {str(e)}")

def _calculate_development_match_score(self, policy: Dict, request, analysis: Dict, is_major: bool) -> float:
    """计算发展政策匹配分数"""
    score = 0.5  # 基础分数

    # 企业规模匹配
    if is_major:
        # 规上企业匹配
        total_income = request.total_income  # 万元
        rd_expense = request.rd_expense  # 万元

        # 研发费用门槛
        if "min_rd_expense" in policy and rd_expense >= policy["min_rd_expense"]:
            score += 0.2

        # 出口业务匹配
        if "min_export" in policy and hasattr(request, 'export_total'):
            if request.export_total >= policy["min_export"] * 10:  # 转千元
                score += 0.15

    else:
        # 普通企业匹配
        total_income = request.total_income  # 千元
        tech_income = request.tech_income
        rd_expense = request.rd_expense
        patent_count = request.valid_patent_count
        invention_patents = request.valid_invention_patent_count

        # 技术收入门槛
        if "min_tech_income" in policy and tech_income >= policy["min_tech_income"]:
            score += 0.15

        # 研发费用门槛
        if "min_rd_expense" in policy and rd_expense >= policy["min_rd_expense"]:
            score += 0.2

        # 专利门槛
        if "min_patents" in policy and patent_count >= policy["min_patents"]:
            score += 0.1

        if "min_invention_patents" in policy and invention_patents >= policy["min_invention_patents"]:
            score += 0.1

        # 企业规模匹配
        if "max_employee" in policy and request.employee_count <= policy["max_employee"]:
            score += 0.1

        if "max_revenue" in policy and total_income <= policy["max_revenue"]:
            score += 0.1

    # 研发人员匹配
    if "min_rd_personnel" in policy and request.rd_personnel_count >= policy["min_rd_personnel"]:
        score += 0.1

    # 基于企业分析调整分数
    financial_capability = analysis.get("financial_capability", "一般")
    rd_capability = analysis.get("rd_capability", "弱")

    if financial_capability == "强":
        score += 0.1
    elif financial_capability == "中":
        score += 0.05

    if rd_capability == "强":
        score += 0.1
    elif rd_capability == "中":
        score += 0.05

    return min(score, 1.0)

def _analyze_matching_indicators(self, policy: Dict, request, analysis: Dict, is_major: bool) -> Dict[str, Any]:
    """分析匹配指标"""
    indicators = {}

    if is_major:
        indicators.update({
            "研发强度": f"{analysis.get('rd_intensity', 0):.1f}%",
            "研发人员比例": f"{analysis.get('rd_personnel_ratio', 0):.1f}%",
            "总收入": f"{request.total_income}万元",
            "研发费用": f"{request.rd_expense}万元"
        })

        if hasattr(request, 'export_total') and request.export_total > 0:
            indicators["出口业务"] = f"{request.export_total}万元"
    else:
        indicators.update({
            "研发强度": f"{analysis.get('rd_intensity', 0):.1f}%",
            "技术收入占比": f"{analysis.get('tech_income_ratio', 0):.1f}%",
            "专利密度": f"{analysis.get('patent_density', 0):.3f}件/人",
            "创新能力": analysis.get('innovation_capability', '低'),
            "有效专利": f"{request.valid_patent_count}件",
            "发明专利": f"{request.valid_invention_patent_count}件"
        })

    return indicators

def _analyze_policy_feasibility(self, policy: Dict, request, analysis: Dict, match_score: float) -> str:
    """分析政策可行性"""
    if match_score >= 0.8:
        return f"高度匹配{policy['policy_name']}，建议优先申请。企业条件符合政策要求，申请成功率较高。"
    elif match_score >= 0.6:
        return f"较好匹配{policy['policy_name']}，建议准备申请材料。需要进一步完善部分申请条件。"
    else:
        return f"部分匹配{policy['policy_name']}，可考虑申请。建议先提升企业相关指标后再申请。"

def _determine_application_priority(self, match_score: float, policy: Dict) -> str:
    """确定申请优先级"""
    if match_score >= 0.8:
        return "高"
    elif match_score >= 0.6:
        return "中"
    else:
        return "低"

def _identify_company_strengths(self, request, analysis: Dict, is_major: bool) -> List[str]:
    """识别企业优势"""
    strengths = []

    # 通用优势分析
    rd_intensity = analysis.get("rd_intensity", 0)
    if rd_intensity >= 5:
        strengths.append(f"研发投入强度高（{rd_intensity:.1f}%），体现了企业对技术创新的重视")
    elif rd_intensity >= 2:
        strengths.append(f"具有一定的研发投入（{rd_intensity:.1f}%），为技术创新提供保障")

    rd_personnel_ratio = analysis.get("rd_personnel_ratio", 0)
    if rd_personnel_ratio >= 15:
        strengths.append(f"研发人员占比较高（{rd_personnel_ratio:.1f}%），技术人才储备充足")
    elif rd_personnel_ratio >= 10:
        strengths.append(f"拥有稳定的研发团队（{rd_personnel_ratio:.1f}%）")

    financial_capability = analysis.get("financial_capability", "一般")
    if financial_capability == "强":
        strengths.append("财务状况良好，具备承担研发投入的经济实力")
    elif financial_capability == "中":
        strengths.append("财务状况稳定，为企业发展提供基础支撑")

    if not is_major:
        # 普通企业特有优势
        tech_income_ratio = analysis.get("tech_income_ratio", 0)
        if tech_income_ratio >= 60:
            strengths.append(f"高新技术收入占比高（{tech_income_ratio:.1f}%），技术产业化能力强")
        elif tech_income_ratio >= 30:
            strengths.append(f"技术收入占比较好（{tech_income_ratio:.1f}%），具有技术转化优势")

        if request.valid_patent_count >= 10:
            strengths.append(f"拥有丰富的知识产权（{request.valid_patent_count}件专利），创新成果突出")
        elif request.valid_patent_count >= 3:
            strengths.append(f"具备一定的知识产权积累（{request.valid_patent_count}件专利）")

        if request.valid_invention_patent_count >= 5:
            strengths.append(f"发明专利数量较多（{request.valid_invention_patent_count}件），创新质量高")
        elif request.valid_invention_patent_count >= 1:
            strengths.append(f"拥有发明专利（{request.valid_invention_patent_count}件），体现技术创新实力")
    else:
        # 规上企业特有优势
        if request.export_total > 0:
            strengths.append(f"具有出口业务（{request.export_total}万元），国际市场拓展能力较好")

        if request.total_income >= 10000:
            strengths.append("企业规模较大，产业化能力和市场影响力强")

    if not strengths:
        strengths.append("企业正在发展阶段，具有提升潜力")

    return strengths

def _identify_improvement_areas(self, request, analysis: Dict, is_major: bool) -> List[str]:
    """识别改进领域"""
    improvements = []

    # 通用改进建议
    rd_intensity = analysis.get("rd_intensity", 0)
    if rd_intensity < 2:
        improvements.append("建议增加研发投入，提高研发费用占营收比例（目前{:.1f}%）".format(rd_intensity))

    rd_personnel_ratio = analysis.get("rd_personnel_ratio", 0)
    if rd_personnel_ratio < 10:
        improvements.append("建议扩充研发团队，提高研发人员占比（目前{:.1f}%）".format(rd_personnel_ratio))

    if not is_major:
        # 普通企业改进建议
        tech_income_ratio = analysis.get("tech_income_ratio", 0)
        if tech_income_ratio < 30:
            improvements.append("建议提高技术收入占比，加强技术成果产业化（目前{:.1f}%）".format(tech_income_ratio))

        if request.valid_patent_count == 0:
            improvements.append("建议加强知识产权申请，建立专利保护体系")
        elif request.valid_patent_count < 3:
            improvements.append("建议继续增加专利申请，提升知识产权竞争力")

        if request.valid_invention_patent_count == 0:
            improvements.append("建议申请发明专利，提升技术创新层次")
    else:
        # 规上企业改进建议
        if request.export_total == 0:
            improvements.append("建议开拓国际市场，发展出口业务")
        elif request.export_total < 1000:
            improvements.append("建议扩大出口规模，提升国际竞争力")

    financial_capability = analysis.get("financial_capability", "一般")
    if financial_capability == "一般":
        improvements.append("建议优化财务结构，提高盈利能力和现金流管理")

    if not improvements:
        improvements.append("企业发展状况良好，建议继续保持并适度扩大投入规模")

    return improvements

def _generate_development_recommendations(self, request, matches: List, is_major: bool) -> List[str]:
    """生成发展建议"""
    recommendations = []

    if not matches:
        recommendations.extend([
            "当前企业条件未找到完全匹配的政策，建议：",
            "1. 优先提升研发投入和技术创新能力",
            "2. 关注政策动态，等待更适合的政策机会",
            "3. 咨询专业机构获得个性化指导"
        ])
        return recommendations

    high_match_count = len([m for m in matches if m.match_level == "高"])
    medium_match_count = len([m for m in matches if m.match_level == "中"])

    if high_match_count > 0:
        recommendations.append(f"发现{high_match_count}个高匹配政策，建议优先申请")
        # 推荐前3个高匹配政策
        high_matches = [m for m in matches if m.match_level == "高"][:3]
        for i, match in enumerate(high_matches, 1):
            recommendations.append(f"{i}. 优先申请：{match.policy_name}")

    if medium_match_count > 0:
        recommendations.append(f"另有{medium_match_count}个中等匹配政策可考虑申请")

    # 基于企业类型的建议
    if is_major:
        recommendations.extend([
            "规上企业专项建议：",
            "1. 充分利用规模优势，申请大额度政策支持",
            "2. 重点关注研发费用补助和税收优惠政策",
            "3. 如有出口业务，积极申请国际市场开拓支持"
        ])
    else:
        recommendations.extend([
            "中小企业专项建议：",
            "1. 重点关注门槛较低、支持力度大的创新政策",
            "2. 加强知识产权保护，提升政策申请竞争力",
            "3. 考虑联合申请或通过服务机构代理申请"
        ])

    recommendations.extend([
        "申请注意事项：",
        "1. 提前准备申请材料，关注申请截止时间",
        "2. 确保企业数据真实准确，避免申请风险",
        "3. 跟踪政策执行情况，及时补充完善材料"
    ])

    return recommendations

# ======= 自测通过率接口 =======

@app.post("/analyze-eligibility", response_model=PolicyEligibilityResponse)
async def analyze_policy_eligibility(request: PolicyEligibilityRequest):
    """
    政策申请通过率自测接口
    
    Args:
        request: 政策资格自测请求
        
    Returns:
        政策资格自测响应
    """
    try:
        logger.info(f"收到自测通过率请求: 政策ID={request.policy_id}, 企业={request.company_info.company_name}")
        
        # 执行政策资格分析
        policy_matcher = get_policy_matcher()
        response = policy_matcher.analyze_policy_eligibility(request)
        
        logger.info(f"自测通过率分析完成: 通过率={response.pass_rate}%, 等级={response.pass_level}")
        return response
        
    except Exception as e:
        logger.error(f"自测通过率分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"自测通过率分析失败: {str(e)}")

@app.get("/eligibility-template")
async def get_eligibility_template():
    """
    获取自测通过率模板数据
    
    Returns:
        模板企业信息和补充信息示例
    """
    try:
        template = {
            "company_info_template": {
                "company_name": "北京某某科技有限公司",
                "company_type": "有限责任公司",
                "registered_capital": "500万元",
                "establishment_date": "2023-01-15",
                "registered_address": "北京市海淀区中关村",
                "business_scope": "人工智能技术研发；软件开发；技术咨询服务",
                "honors_qualifications": ["中关村高新技术企业"]
            },
            "additional_info_template": {
                "rd_expense_ratio": 8.5,
                "rd_personnel_ratio": 15.0,
                "high_tech_income_ratio": 75.0,
                "has_financial_audit": True,
                "has_project_plan": True,
                "annual_revenue": 1200.0,
                "total_employees": 25,
                "rd_employees": 8,
                "patents_count": 3,
                "software_copyrights_count": 5
            },
            "field_descriptions": {
                "rd_expense_ratio": "研发费用占营业收入比例（%）",
                "rd_personnel_ratio": "研发人员占企业总人数比例（%）",
                "high_tech_income_ratio": "高新技术产品收入占总收入比例（%）",
                "has_financial_audit": "是否有近三年财务审计报告",
                "has_project_plan": "是否有详细的项目计划",
                "annual_revenue": "年营业收入（万元）",
                "total_employees": "企业总人数",
                "rd_employees": "研发人员数量",
                "patents_count": "发明专利数量",
                "software_copyrights_count": "软件著作权数量"
            }
        }
        
        return template
        
    except Exception as e:
        logger.error(f"获取模板失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模板失败: {str(e)}")

@app.get("/policy-conditions/{policy_id}")
async def get_policy_conditions_info(policy_id: str):
    """
    获取政策申请条件信息
    
    Args:
        policy_id: 政策ID
        
    Returns:
        政策条件详情
    """
    try:
        logger.info(f"查询政策条件信息: {policy_id}")
        
        # 模拟政策条件信息
        conditions_info = {
            "policy_id": policy_id,
            "policy_name": "北京市高新技术企业认定政策",
            "policy_type": "资质认定",
            "basic_conditions": [
                {
                    "condition": "企业注册成立满一年",
                    "description": "企业在中国境内注册成立满365天以上",
                    "importance": "必要条件",
                    "weight": 20
                },
                {
                    "condition": "经营范围符合要求",
                    "description": "企业经营范围应包含技术开发、技术服务等",
                    "importance": "必要条件",
                    "weight": 15
                }
            ],
            "specific_conditions": [
                {
                    "condition": "拥有自主知识产权",
                    "description": "企业应拥有发明专利、实用新型专利、软件著作权等",
                    "importance": "必要条件",
                    "weight": 15
                },
                {
                    "condition": "研发人员占比达标",
                    "description": "研发人员占企业当年职工总数的比例不低于10%",
                    "importance": "必要条件",
                    "weight": 10
                },
                {
                    "condition": "研发费用占比达到要求", 
                    "description": "企业近三个会计年度研发费用总额占同期销售收入总额的比例不低于规定标准",
                    "importance": "必要条件",
                    "weight": 15
                },
                {
                    "condition": "高新技术产品收入占比达标",
                    "description": "高新技术产品（服务）收入占企业当年总收入的比例不低于60%",
                    "importance": "必要条件",
                    "weight": 15
                }
            ],
            "scoring_rules": {
                "total_weight": 100,
                "pass_threshold": 70,
                "evaluation_levels": {
                    "高": "≥70分",
                    "中": "40-69分",
                    "低": "<40分"
                }
            }
        }
        
        return conditions_info
        
    except Exception as e:
        logger.error(f"获取政策条件信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取政策条件信息失败: {str(e)}")

@app.get("/config")
async def get_config():
    """
    获取配置选项
    
    Returns:
        系统配置信息
    """
    try:
        config_data = {
            "industries": [
                "生物医药（含医疗器械）",
                "先进能源", 
                "智能制造",
                "新一代信息技术",
                "科技服务",
                "其他"
            ],
            "company_scales": [
                "初创企业（成立<3年，员工<20人）",
                "中小企业（员工20-200人）",
                "大型企业（员工>200人）"
            ],
            "demand_types": [
                "资金补贴（如研发费用补助）",
                "资质认定（如高新企业、专精特新）",
                "人才支持（如落户、住房补贴）",
                "空间/设备（如实验室租金减免）"
            ],
            "policy_types": [
                "资金支持",
                "资质认定",
                "人才政策", 
                "税收优惠",
                "产业扶持",
                "创新支持"
            ],
            "regions": [
                "北京",
                "上海",
                "深圳",
                "广州",
                "杭州",
                "南京",
                "成都",
                "武汉"
            ]
        }
        
        return config_data
        
    except Exception as e:
        logger.error(f"配置获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置获取失败: {str(e)}")

@app.get("/company-info/{company_name}")
async def get_company_info(company_name: str):
    """
    获取企业信息（模拟接口）
    
    Args:
        company_name: 企业名称
        
    Returns:
        企业基础信息
    """
    try:
        logger.info(f"查询企业信息: {company_name}")
        
        # 模拟企业信息数据
        mock_company_info = {
            "company_name": company_name,
            "company_type": "有限责任公司",
            "registered_capital": "1000万元",
            "establishment_date": "2022-03-15",
            "registered_address": "北京市海淀区中关村南大街",
            "business_scope": "技术开发、技术咨询、技术服务；销售电子产品、计算机软硬件",
            "legal_representative": "张三",
            "status": "存续",
            "credit_code": "91110000000000000X",
            "honors_qualifications": [
                "中关村高新技术企业",
                "科技型中小企业"
            ]
        }
        
        return mock_company_info
        
    except Exception as e:
        logger.error(f"企业信息查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"企业信息查询失败: {str(e)}")

# ======= 文档管理接口 =======

@app.post("/upload")
async def upload_policy_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    上传政策文档接口
    
    Args:
        file: 上传的文件
        
    Returns:
        上传结果
    """
    try:
        # 检查文件类型
        allowed_extensions = {'.pdf', '.docx', '.txt'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 保存临时文件
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=file_extension,
            prefix="policy_"
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # 后台处理文档
        background_tasks.add_task(process_uploaded_document, temp_file_path, file.filename)
        
        return {
            "message": "文件上传成功，正在后台处理",
            "filename": file.filename,
            "size": len(content),
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

async def process_uploaded_document(file_path: str, original_filename: str):
    """
    后台处理上传的文档
    
    Args:
        file_path: 临时文件路径
        original_filename: 原始文件名
    """
    try:
        logger.info(f"开始处理上传文档: {original_filename}")
        
        # 添加文档到系统
        policy_matcher = get_policy_matcher()
        success = policy_matcher.add_policy_document(file_path)
        
        if success:
            logger.info(f"文档处理成功: {original_filename}")
        else:
            logger.error(f"文档处理失败: {original_filename}")
            
    except Exception as e:
        logger.error(f"后台处理文档失败: {e}")
    finally:
        # 清理临时文件
        try:
            os.unlink(file_path)
        except:
            pass

# ======= 系统状态接口 =======

@app.get("/status", response_model=SystemStatus)
async def get_system_status():
    """
    获取系统状态
    
    Returns:
        系统状态信息
    """
    try:
        policy_matcher = get_policy_matcher()
        status_info = policy_matcher.get_system_status()
        
        return SystemStatus(
            status=status_info.get("status", "未知"),
            total_policies=status_info.get("vector_store", {}).get("milvus_stats", {}).get("row_count", 0),
            total_chunks=status_info.get("vector_store", {}).get("milvus_stats", {}).get("row_count", 0),
            vector_store_status="正常" if status_info.get("vector_store", {}).get("milvus_connected") else "异常",
            elasticsearch_status="正常" if status_info.get("vector_store", {}).get("elasticsearch_connected") else "异常",
            last_update="2024-01-01T00:00:00"  # 这里应该从数据库获取实际的更新时间
        )
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")

@app.get("/health")
async def health_check():
    """
    健康检查接口
    
    Returns:
        健康状态
    """
    try:
        # 检查各组件状态
        policy_matcher = get_policy_matcher()
        status_info = policy_matcher.get_system_status()
        
        # 简单的健康检查
        is_healthy = (
            status_info.get("vector_store", {}).get("milvus_connected", False) and
            status_info.get("vector_store", {}).get("elasticsearch_connected", False) and
            status_info.get("embedding_model", {}).get("status") == "loaded"
        )
        
        if is_healthy:
            return {"status": "healthy", "timestamp": "2024-01-01T00:00:00"}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "details": status_info}
            )
            
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "error": str(e)}
        )

# ======= 帮助和示例接口 =======

@app.get("/examples")
async def get_query_examples():
    """
    获取查询示例
    
    Returns:
        查询示例列表
    """
    examples = {
        "natural_language": [
            {
                "query": "我想查找和生物医药相关的政策",
                "description": "按行业查找政策",
                "expected_results": "返回生物医药、医疗器械、制药等相关政策"
            },
            {
                "query": "我是一家小型初创企业，现阶段有什么政策比较适用",
                "description": "按企业规模查找政策",
                "expected_results": "返回适合初创企业的政策，过滤高门槛政策"
            },
            {
                "query": "有哪些研发创新方面的资金支持政策",
                "description": "按政策类型查找",
                "expected_results": "返回创新研发相关的资金支持政策"
            }
        ],
        "basic_match": {
            "industry": "生物医药（含医疗器械）",
            "company_scale": "初创企业（成立<3年，员工<20人）",
            "demand_type": "资金补贴（如研发费用补助）"
        },
        "precise_match": {
            "basic_request": {
                "industry": "新一代信息技术",
                "company_scale": "初创企业（成立<3年，员工<20人）",
                "demand_type": "资质认定（如高新企业、专精特新）"
            },
            "company_info": {
                "company_name": "北京智能科技有限公司",
                "company_type": "有限责任公司",
                "registered_capital": "500万元",
                "establishment_date": "2023-01-15",
                "registered_address": "北京市海淀区中关村",
                "business_scope": "人工智能技术研发；软件开发",
                "honors_qualifications": ["中关村高新技术企业"]
            }
        }
    }
    
    return {"examples": examples}

@app.get("/categories")
async def get_policy_categories():
    """
    获取政策分类信息
    
    Returns:
        政策分类列表
    """
    try:
        from config import config
        
        categories = {
            "industries": list(config.INDUSTRY_MAPPING.keys()),
            "enterprise_scales": list(config.ENTERPRISE_SCALES.keys()),
            "policy_types": list(config.POLICY_TYPES.keys())
        }
        
        return categories
    except:
        # 如果config模块有问题，返回默认分类
        return {
            "industries": ["生物医药", "信息技术", "新能源", "智能制造"],
            "enterprise_scales": ["初创企业", "中小企业", "大型企业"],
            "policy_types": ["资金支持", "资质认定", "人才政策", "税收优惠"]
        }

# 异常处理
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    logger.error(f"值错误: {exc}")
    return JSONResponse(
        status_code=400,
        content={"error": "请求参数错误", "detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"未捕获的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误", "detail": "请联系管理员"}
    )

if __name__ == "__main__":
    import uvicorn
    
    logger.info("启动政策匹配API服务...")
    
    try:
        # 预加载系统组件
        logger.info("正在初始化系统...")
        status = policy_matcher.get_system_status()
        logger.info(f"系统状态: {status}")
        
        # 启动服务
        uvicorn.run(app, host="0.0.0.0", port=8000)
        
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        exit(1) 