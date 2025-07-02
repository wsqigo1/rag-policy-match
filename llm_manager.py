import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
import requests
from dataclasses import dataclass
from enum import Enum

from config import config

logger = logging.getLogger(__name__)

class PromptType(Enum):
    """提示类型枚举"""
    POLICY_SUMMARY = "policy_summary"
    ELIGIBILITY_ANALYSIS = "eligibility_analysis"
    POLICY_MATCHING = "policy_matching"
    RERANK = "rerank"
    OPTIMIZATION_STRATEGY = "optimization_strategy"
    QUERY_UNDERSTANDING = "query_understanding"

@dataclass
class LLMRequest:
    """LLM请求数据类"""
    prompt: str
    system_prompt: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    stream: bool = False

@dataclass
class LLMResponse:
    """LLM响应数据类"""
    content: str
    usage: Dict[str, int]
    model: str
    success: bool = True
    error: Optional[str] = None

class PromptTemplateManager:
    """提示模板管理器"""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """加载提示模板"""
        return {
            PromptType.POLICY_SUMMARY.value: {
                "system": """你是一个专业的政策分析专家。请根据提供的政策文档内容，生成准确、简洁、结构化的政策摘要。

要求：
1. 提取政策核心信息：名称、目的、适用对象、支持内容、申请条件、申请流程
2. 使用清晰的结构化格式
3. 突出重点信息，避免冗余
4. 确保信息准确性""",
                
                "user": """请分析以下政策内容并生成摘要：

政策内容：
{policy_content}

请按以下格式输出：
## 政策摘要

**政策名称：** [政策名称]
**政策目的：** [简要说明政策目标和意义]
**适用对象：** [明确说明哪些企业或个人可以申请]
**支持内容：** [具体支持措施，如资金、服务等]
**申请条件：** [关键申请条件]
**申请流程：** [简要流程步骤]

**重点提示：** [需要特别注意的事项]"""
            },
            
            PromptType.ELIGIBILITY_ANALYSIS.value: {
                "system": """你是一个政策适用性分析专家。请根据企业信息和政策要求，准确分析企业的申请资格和通过可能性。

分析要点：
1. 逐项对比企业条件与政策要求
2. 识别已满足和待完善的条件
3. 评估整体通过率
4. 提供具体的改进建议""",
                
                "user": """请分析以下企业对指定政策的申请资格：

企业信息：
{company_info}

政策要求：
{policy_requirements}

请按以下格式分析：
## 资格分析报告

### 已满足条件
[列出企业已满足的申请条件，说明具体符合情况]

### 待完善条件  
[列出需要改进的条件，说明具体差距]

### 通过率评估
**预估通过率：** [数字]%
**风险等级：** [高/中/低]

### 改进建议
[提供具体的改进措施和时间安排]"""
            },
            
            PromptType.POLICY_MATCHING.value: {
                "system": """你是一个智能政策匹配专家。请根据用户查询和检索到的政策信息，提供最相关和有用的政策推荐。

分析要点：
1. 理解用户真实需求
2. 评估政策相关性和适用性
3. 提供个性化推荐理由
4. 给出实用的申请建议""",
                
                "user": """用户查询：{user_query}

检索到的政策信息：
{retrieved_policies}

企业信息（如有）：
{company_context}

请提供政策匹配分析：
## 政策推荐

### 最相关政策
[按相关性排序，说明推荐理由]

### 适用性分析
[分析各政策对该企业的适用性]

### 申请建议
[提供具体的申请顺序和准备事项]"""
            },
            
            PromptType.RERANK.value: {
                "system": """你是一个信息相关性评估专家。请根据用户查询，对检索结果进行相关性重新排序。

评估标准：
1. 内容与查询的语义相关性
2. 信息的完整性和准确性
3. 对用户的实用价值
4. 信息的时效性和权威性""",
                
                "user": """用户查询：{query}

候选结果：
{candidates}

请按相关性从高到低重新排序，并说明排序理由：
## 重排结果

[按格式输出：排名. 结果ID - 简要理由]"""
            },
            
            PromptType.OPTIMIZATION_STRATEGY.value: {
                "system": """你是一个政策申请优化策略专家。请根据分析结果，动态生成个性化的优化策略。

策略要点：
1. 基于企业实际情况
2. 考虑政策申请成功率
3. 平衡投入产出比
4. 提供可执行的行动计划""",
                
                "user": """企业现状：
{company_status}

政策分析结果：
{analysis_results}

目标政策：
{target_policies}

请生成优化策略：
## 优化策略方案

### 优先级策略
[按优先级排序的申请策略]

### 能力提升计划
[针对性的能力建设建议]

### 时间规划
[申请时间安排和里程碑]

### 风险控制
[潜在风险和应对措施]"""
            },
            
            PromptType.QUERY_UNDERSTANDING.value: {
                "system": """你是一个查询理解专家。请分析用户的自然语言查询，提取关键信息和意图。

分析要点：
1. 识别查询意图类型
2. 提取实体信息（行业、规模、地区等）
3. 理解隐含需求
4. 生成优化的搜索策略""",
                
                "user": """用户查询：{query}

请分析并输出：
## 查询分析

**主要意图：** [find_policy/check_eligibility/get_funding/get_requirements]
**查询复杂度：** [simple/moderate/complex]
**关键实体：**
- 行业领域：[提取的行业]
- 企业规模：[提取的规模]
- 地区信息：[提取的地区]
- 政策类型：[提取的类型]

**优化查询：** [生成的搜索关键词]
**检索策略：** [推荐的检索方法]"""
            }
        }
    
    def get_prompt(self, prompt_type: PromptType, **kwargs) -> tuple[str, str]:
        """获取格式化的提示"""
        template = self.templates.get(prompt_type.value)
        if not template:
            raise ValueError(f"未找到提示模板: {prompt_type.value}")
        
        system_prompt = template["system"]
        user_prompt = template["user"].format(**kwargs)
        
        return system_prompt, user_prompt

class DeepSeekLLMManager:
    """DeepSeek大模型管理器"""
    
    def __init__(self):
        self.api_base = config.DEEPSEEK_API_BASE
        self.api_key = config.DEEPSEEK_API_KEY
        self.model = config.DEEPSEEK_MODEL
        self.template_manager = PromptTemplateManager()
        
        if not self.api_key:
            logger.warning("未设置DeepSeek API密钥，LLM功能将被禁用")
    
    def _prepare_headers(self) -> Dict[str, str]:
        """准备请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def _call_api(self, request: LLMRequest) -> LLMResponse:
        """调用DeepSeek API"""
        if not self.api_key:
            return LLMResponse(
                content="",
                usage={},
                model=self.model,
                success=False,
                error="未配置API密钥"
            )
        
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt}
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": request.stream
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=self._prepare_headers(),
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    usage=data.get("usage", {}),
                    model=data.get("model", self.model),
                    success=True
                )
            else:
                logger.error(f"DeepSeek API错误: {response.status_code} - {response.text}")
                return LLMResponse(
                    content="",
                    usage={},
                    model=self.model,
                    success=False,
                    error=f"API错误: {response.status_code}"
                )
                
        except Exception as e:
            logger.error(f"调用DeepSeek API失败: {e}")
            return LLMResponse(
                content="",
                usage={},
                model=self.model,
                success=False,
                error=str(e)
            )
    
    def generate_policy_summary(self, policy_content: str) -> LLMResponse:
        """生成政策摘要"""
        system_prompt, user_prompt = self.template_manager.get_prompt(
            PromptType.POLICY_SUMMARY,
            policy_content=policy_content
        )
        
        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=2048
        )
        
        return self._call_api(request)
    
    def analyze_eligibility(self, company_info: Dict, policy_requirements: str) -> LLMResponse:
        """分析企业资格"""
        company_text = self._format_company_info(company_info)
        
        system_prompt, user_prompt = self.template_manager.get_prompt(
            PromptType.ELIGIBILITY_ANALYSIS,
            company_info=company_text,
            policy_requirements=policy_requirements
        )
        
        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=3072
        )
        
        return self._call_api(request)
    
    def match_policies(self, user_query: str, retrieved_policies: List[Dict], 
                      company_context: Optional[Dict] = None) -> LLMResponse:
        """政策匹配分析"""
        policies_text = self._format_policies(retrieved_policies)
        company_text = self._format_company_info(company_context) if company_context else "无企业信息"
        
        system_prompt, user_prompt = self.template_manager.get_prompt(
            PromptType.POLICY_MATCHING,
            user_query=user_query,
            retrieved_policies=policies_text,
            company_context=company_text
        )
        
        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=3072
        )
        
        return self._call_api(request)
    
    def rerank_results(self, query: str, candidates: List[Dict]) -> LLMResponse:
        """LLM重排"""
        candidates_text = self._format_candidates(candidates)
        
        system_prompt, user_prompt = self.template_manager.get_prompt(
            PromptType.RERANK,
            query=query,
            candidates=candidates_text
        )
        
        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=2048
        )
        
        return self._call_api(request)
    
    def generate_optimization_strategy(self, company_status: Dict, 
                                     analysis_results: Dict,
                                     target_policies: List[Dict]) -> LLMResponse:
        """生成优化策略"""
        company_text = self._format_company_info(company_status)
        analysis_text = json.dumps(analysis_results, ensure_ascii=False, indent=2)
        policies_text = self._format_policies(target_policies)
        
        system_prompt, user_prompt = self.template_manager.get_prompt(
            PromptType.OPTIMIZATION_STRATEGY,
            company_status=company_text,
            analysis_results=analysis_text,
            target_policies=policies_text
        )
        
        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.4,
            max_tokens=4096
        )
        
        return self._call_api(request)
    
    def understand_query(self, query: str) -> LLMResponse:
        """查询理解"""
        system_prompt, user_prompt = self.template_manager.get_prompt(
            PromptType.QUERY_UNDERSTANDING,
            query=query
        )
        
        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=1024
        )
        
        return self._call_api(request)
    
    def _format_company_info(self, company_info: Optional[Dict]) -> str:
        """格式化企业信息"""
        if not company_info:
            return "无企业信息"
        
        formatted = []
        for key, value in company_info.items():
            if value:
                formatted.append(f"- {key}: {value}")
        
        return "\n".join(formatted)
    
    def _format_policies(self, policies: List[Dict]) -> str:
        """格式化政策信息"""
        formatted = []
        for i, policy in enumerate(policies, 1):
            content = policy.get('content', policy.get('summary', '无内容'))
            title = policy.get('title', policy.get('policy_id', f'政策{i}'))
            formatted.append(f"{i}. {title}\n{content}\n")
        
        return "\n".join(formatted)
    
    def _format_candidates(self, candidates: List[Dict]) -> str:
        """格式化候选结果"""
        formatted = []
        for i, candidate in enumerate(candidates, 1):
            content = candidate.get('content', '无内容')
            chunk_id = candidate.get('chunk_id', f'result_{i}')
            score = candidate.get('score', 0)
            formatted.append(f"{i}. ID: {chunk_id} (分数: {score:.3f})\n内容: {content[:200]}...\n")
        
        return "\n".join(formatted)
    
    # 为了向后兼容，添加policy_matcher中使用的方法
    async def initialize(self):
        """初始化（异步兼容）"""
        pass
    
    async def generate_policy_analysis(self, prompt: str, context: Dict) -> str:
        """生成政策分析（异步兼容）"""
        request = LLMRequest(
            prompt=prompt,
            system_prompt="你是一个专业的政策分析专家。",
            temperature=0.3,
            max_tokens=2048
        )
        
        response = self._call_api(request)
        return response.content if response.success else "分析失败"
    
    async def understand_query_async(self, query: str) -> Dict[str, Any]:
        """异步查询理解"""
        response = self.understand_query(query)
        if response.success:
            try:
                # 尝试解析结构化输出
                content = response.content
                result = {
                    "intent": "find_policy",
                    "complexity": "moderate",
                    "entities": {},
                    "optimized_query": query,
                    "strategy": "semantic_search"
                }
                return result
            except:
                return {"intent": "find_policy", "analysis": response.content}
        else:
            return {"intent": "find_policy", "error": response.error}
    
    async def generate_personalized_recommendation(self, results: List, company_info) -> str:
        """生成个性化推荐"""
        if not results:
            return "未找到相关政策，建议扩大搜索范围或联系政策咨询部门。"
        
        try:
            policies_data = []
            for result in results[:3]:  # 只分析前3个结果
                policies_data.append({
                    "title": getattr(result, 'title', '政策'),
                    "content": getattr(result, 'content', '')[:200],
                    "score": getattr(result, 'score', 0)
                })
            
            response = self.match_policies(
                user_query="个性化政策推荐",
                retrieved_policies=policies_data,
                company_context=company_info.__dict__ if hasattr(company_info, '__dict__') else company_info
            )
            
            return response.content if response.success else "推荐分析失败，请手动查看政策详情。"
        
        except Exception as e:
            logger.error(f"生成个性化推荐失败: {e}")
            return f"找到{len(results)}个相关政策，建议根据企业实际情况逐一评估申请可行性。"

# 为了向后兼容，提供LLMManager别名
LLMManager = DeepSeekLLMManager

# 全局LLM管理器实例
_llm_manager = None

def get_llm_manager() -> DeepSeekLLMManager:
    """获取LLM管理器实例"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = DeepSeekLLMManager()
    return _llm_manager

# 向后兼容
def __getattr__(name):
    if name == 'llm_manager':
        return get_llm_manager()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 