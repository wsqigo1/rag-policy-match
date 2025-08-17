import re
import fitz  # PyMuPDF
import pdfplumber
import docx2txt
import jieba
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import logging
# from docx import Document as DocxDocument  # 暂时注释掉，需要时再启用

from models import PolicyDocument, PolicyChunk, StructuredPolicy
from config import config, Config

logger = logging.getLogger(__name__)

class StructuredPolicyExtractor:
    """结构化政策信息提取器"""
    
    def __init__(self):
        # 结构化字段的正则模式
        self.field_patterns = {
            'basis_document': [
                r'依据文件[：:]\s*(.*?)(?=\n|$)',
                r'制定依据[：:]\s*(.*?)(?=\n|$)',
                r'政策依据[：:]\s*(.*?)(?=\n|$)'
            ],
            'issuing_agency': [
                r'发文机构[：:]\s*(.*?)(?=\n|$)',
                r'制定单位[：:]\s*(.*?)(?=\n|$)',
                r'发布单位[：:]\s*(.*?)(?=\n|$)',
                r'主管部门[：:]\s*(.*?)(?=\n|$)'
            ],
            'document_number': [
                r'发文字号[：:]\s*(.*?)(?=\n|$)',
                r'文件编号[：:]\s*(.*?)(?=\n|$)',
                r'([京津沪渝黑吉辽蒙冀豫鲁苏皖浙闽赣湘鄂桂琼川贵滇藏陕甘宁青新].*?[〔\[]\d{4}[〕\]]\s*\d+\s*号)',
            ],
            'issue_date': [
                r'发布日期[：:]\s*(.*?)(?=\n|$)',
                r'印发日期[：:]\s*(.*?)(?=\n|$)',
                r'生效日期[：:]\s*(.*?)(?=\n|$)',
                r'(\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?)',
            ],
            'tool_category': [
                r'工具分类[：:]\s*(.*?)(?=\n|$)',
                r'政策类型[：:]\s*(.*?)(?=\n|$)',
                r'支持方式[：:]\s*(.*?)(?=\n|$)',
                r'(资金支持|政策支持|税收优惠|平台支持|人才支持)'
            ],
            'service_object': [
                r'服务对象[：:]\s*(.*?)(?=\n|$)',
                r'适用对象[：:]\s*(.*?)(?=\n|$)',
                r'申请主体[：:]\s*(.*?)(?=\n|$)'
            ],
            'service_content': [
                r'服务内容[：:]\s*(.*?)(?=\n|$)',
                r'支持内容[：:]\s*(.*?)(?=\n|$)',
                r'主要内容[：:]\s*(.*?)(?=\n|$)'
            ],
            'condition_requirements': [
                r'条件要求[：:]\s*(.*?)(?=\n|$)',
                r'申请条件[：:]\s*(.*?)(?=\n|$)',
                r'基本条件[：:]\s*(.*?)(?=\n|$)',
                r'资格要求[：:]\s*(.*?)(?=\n|$)'
            ],
            'service_process': [
                r'服务流程[：:]\s*(.*?)(?=\n|$)',
                r'申请流程[：:]\s*(.*?)(?=\n|$)',
                r'办理流程[：:]\s*(.*?)(?=\n|$)'
            ],
            'time_frequency': [
                r'时间[/／]频度[：:]\s*(.*?)(?=\n|$)',
                r'申请时间[：:]\s*(.*?)(?=\n|$)',
                r'受理时间[：:]\s*(.*?)(?=\n|$)',
                r'常年受理|随时申请|按批次|每年\d+次|定期'
            ],
            'contact_info': [
                r'联络方式[：:]\s*(.*?)(?=\n|$)',
                r'联系方式[：:]\s*(.*?)(?=\n|$)',
                r'咨询电话[：:]\s*(.*?)(?=\n|$)',
                r'(\d{3,4}[-\s]?\d{7,8}|\d{11})'
            ]
        }
        
        # 关键信息提取模式
        self.analysis_patterns = {
            'industries': [
                r'(生物医药|人工智能|集成电路|新能源|新材料|高端装备|节能环保|数字创意|软件信息|航空航天|海洋工程)',
                r'(制造业|服务业|农业|建筑业|采矿业|金融业|房地产业|批发零售业|交通运输业|信息技术业)'
            ],
            'enterprise_scales': [
                r'(大型企业|中型企业|小型企业|微型企业)',
                r'(初创企业|成长型企业|成熟企业)',
                r'(上市公司|非上市公司)',
                r'(国有企业|民营企业|外资企业)'
            ],
            'support_amounts': [
                r'(\d+(?:\.\d+)?)\s*(?:万元|万|万人民币)',
                r'(\d+(?:\.\d+)?)\s*(?:亿元|亿)',
                r'最高[支持]?(?:金额)?[：:]?\s*(\d+(?:\.\d+)?)\s*(?:万元|万|亿元|亿)',
                r'不超过\s*(\d+(?:\.\d+)?)\s*(?:万元|万|亿元|亿)'
            ]
        }

    def extract_structured_fields(self, content: str) -> Dict[str, Any]:
        """提取结构化字段"""
        extracted = {}
        
        # 提取主要结构化字段
        for field_name, patterns in self.field_patterns.items():
            extracted[field_name] = self._extract_field_value(content, patterns)
        
        # 提取分析字段
        extracted['industries'] = self._extract_list_values(content, self.analysis_patterns['industries'])
        extracted['enterprise_scales'] = self._extract_list_values(content, self.analysis_patterns['enterprise_scales'])
        extracted['support_amount_range'] = self._extract_support_amounts(content)
        
        return extracted

    def _extract_field_value(self, content: str, patterns: List[str]) -> Optional[str]:
        """提取单个字段值"""
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if match.groups():
                    value = match.group(1).strip()
                    if value and len(value) > 3:  # 过滤太短的匹配
                        return value
                else:
                    return match.group(0).strip()
        return None

    def _extract_list_values(self, content: str, patterns: List[str]) -> List[str]:
        """提取列表值"""
        values = set()
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    values.add(match.group(1))
                else:
                    values.add(match.group(0))
        return list(values)

    def _extract_support_amounts(self, content: str) -> Dict[str, Any]:
        """提取支持金额范围"""
        amounts = []
        for pattern in self.analysis_patterns['support_amounts']:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match.group(1))
                    if '亿' in match.group(0):
                        amount *= 10000  # 转换为万元
                    amounts.append(amount)
                except (ValueError, IndexError):
                    continue
        
        if amounts:
            return {
                'min_amount': min(amounts),
                'max_amount': max(amounts),
                'amounts': amounts
            }
        return {}

class DocumentProcessor:
    """增强的文档处理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.extractor = StructuredPolicyExtractor()
        
        # 初始化正则表达式模式
        self.money_pattern = re.compile(r'(\d+(?:\.\d+)?(?:万|千|亿)?元?)')
        self.requirement_pattern = re.compile(r'(?:应当|必须|需要|要求|条件|资格|标准)', re.IGNORECASE)
        self.title_pattern = re.compile(r'^[一二三四五六七八九十\d]+[、．.]', re.IGNORECASE)
        self.section_pattern = re.compile(r'^第[一二三四五六七八九十\d]+[章节条款]', re.IGNORECASE)
        
    def process_pdf(self, pdf_path: str) -> PolicyDocument:
        """处理PDF文档并提取结构化信息"""
        logger.info(f"Processing PDF: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                pages_content = []
                
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    full_text += page_text + "\n"
                    pages_content.append({
                        'page_num': i + 1,
                        'content': page_text
                    })
                
                # 提取结构化字段
                structured_fields = self.extractor.extract_structured_fields(full_text)
                
                # 创建结构化政策对象
                structured_policy = StructuredPolicy(
                    policy_id=Path(pdf_path).stem,
                    title=self._extract_title(full_text),
                    full_content=full_text,
                    original_filename=Path(pdf_path).name,  # 添加原始文件名
                    file_path=pdf_path,  # 添加文件路径
                    **structured_fields
                )
                
                # 创建分块
                chunks = self._create_enhanced_chunks(
                    full_text, 
                    pages_content, 
                    structured_policy
                )
                structured_policy.chunks = chunks
                
                return PolicyDocument(
                    document_id=Path(pdf_path).stem,
                    title=structured_policy.title,
                    content=full_text,
                    chunks=chunks,
                    metadata={
                        'source': pdf_path,
                        'type': 'pdf',
                        'structured_policy': structured_policy.__dict__
                    }
                )
                
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise

    def _extract_title(self, content: str) -> str:
        """提取政策标题"""
        lines = content.split('\n')
        for line in lines[:10]:  # 检查前10行
            line = line.strip()
            if len(line) > 10 and not line.startswith(('附件', '文件', '编号')):
                return line
        return "未知政策标题"

    def _create_enhanced_chunks(self, content: str, pages_content: List[Dict], 
                               structured_policy: StructuredPolicy) -> List[PolicyChunk]:
        """创建增强的分块，包含结构化信息"""
        chunks = []
        
        # 分段处理
        sections = self._split_into_sections(content)
        
        for i, section in enumerate(sections):
            if len(section.strip()) < 50:  # 跳过太短的段落
                continue
                
            chunk_id = f"{structured_policy.policy_id}_chunk_{i}"
            
            # 确定chunk类型和重要性
            chunk_type, section_name = self._classify_chunk(section)
            
            chunk = PolicyChunk(
                chunk_id=chunk_id,
                policy_id=structured_policy.policy_id,
                content=section,
                section=section_name,
                chunk_type=chunk_type,
                keywords=self._extract_keywords(section),
                
                # 继承结构化字段
                basis_document=structured_policy.basis_document,
                issuing_agency=structured_policy.issuing_agency,
                document_number=structured_policy.document_number,
                issue_date=structured_policy.issue_date,
                tool_category=structured_policy.tool_category,
                service_object=structured_policy.service_object,
                service_content=structured_policy.service_content,
                condition_requirements=structured_policy.condition_requirements,
                service_process=structured_policy.service_process,
                time_frequency=structured_policy.time_frequency,
                contact_info=structured_policy.contact_info,
                
                # 分析相关字段
                policy_level=self._determine_policy_level(structured_policy.issuing_agency),
                support_amount=str(structured_policy.support_amount_range) if structured_policy.support_amount_range else None,
            )
            
            chunks.append(chunk)
        
        return chunks

    def _split_into_sections(self, content: str) -> List[str]:
        """智能分段"""
        # 按标题和段落分割
        patterns = [
            r'\n\s*[一二三四五六七八九十]\s*[、．.]\s*',  # 中文数字标题
            r'\n\s*\d+\s*[、．.]\s*',  # 阿拉伯数字标题
            r'\n\s*[（(]\s*[一二三四五六七八九十]\s*[）)]\s*',  # 括号中文数字
            r'\n\s*[（(]\s*\d+\s*[）)]\s*',  # 括号阿拉伯数字
            r'\n\s*第[一二三四五六七八九十\d]+[章节条款项]\s*',  # 第X章节
        ]
        
        # 找到所有分割点
        split_points = [0]
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                split_points.append(match.start())
        
        split_points.append(len(content))
        split_points = sorted(set(split_points))
        
        # 创建段落
        sections = []
        for i in range(len(split_points) - 1):
            section = content[split_points[i]:split_points[i + 1]].strip()
            if section:
                sections.append(section)
        
        return sections

    def _classify_chunk(self, content: str) -> Tuple[str, str]:
        """分类chunk类型和段落名称"""
        content_lower = content.lower()
        
        # 根据内容判断类型和名称
        if any(keyword in content_lower for keyword in ['条件要求', '申请条件', '基本条件']):
            return 'condition', '条件要求'
        elif any(keyword in content_lower for keyword in ['服务内容', '支持内容', '主要内容']):
            return 'service', '服务内容'
        elif any(keyword in content_lower for keyword in ['服务流程', '申请流程', '办理流程']):
            return 'process', '服务流程'
        elif any(keyword in content_lower for keyword in ['联系方式', '联络方式', '咨询电话']):
            return 'contact', '联络方式'
        elif any(keyword in content_lower for keyword in ['服务对象', '适用对象']):
            return 'target', '服务对象'
        else:
            return 'general', '一般内容'

    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        import jieba
        
        # 分词
        words = jieba.lcut(content)
        
        # 过滤停用词和短词
        stop_words = {'的', '是', '在', '有', '和', '与', '或', '等', '及', '对', '为', '以', '按', '由'}
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        
        # 返回出现频次较高的词
        from collections import Counter
        word_freq = Counter(keywords)
        return [word for word, freq in word_freq.most_common(10)]

    def _determine_policy_level(self, issuing_agency: Optional[str]) -> str:
        """确定政策级别"""
        if not issuing_agency:
            return "未知"
        
        agency_lower = issuing_agency.lower()
        if any(keyword in agency_lower for keyword in ['国务院', '发改委', '工信部', '科技部']):
            return "国家级"
        elif any(keyword in agency_lower for keyword in ['北京市', '市政府', '市委']):
            return "市级"
        elif any(keyword in agency_lower for keyword in ['区政府', '区委', '街道']):
            return "区级"
        else:
            return "其他"

    def extract_text_from_pdf(self, file_path: str) -> Tuple[str, List[Dict]]:
        """从PDF提取文本和表格"""
        try:
            # 使用PyMuPDF提取文本
            doc = fitz.open(file_path)
            text_content = ""
            tables = []
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                text_content += page.get_text()
            
            doc.close()
            
            # 使用pdfplumber提取表格
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table:  # 确保表格不为空
                            tables.append({
                                'page': page_num + 1,
                                'content': table,
                                'text': self._table_to_text(table)
                            })
            
            return text_content, tables
            
        except Exception as e:
            logger.error(f"PDF解析失败 {file_path}: {e}")
            return "", []
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """从DOCX提取文本"""
        try:
            return docx2txt.process(file_path)
        except Exception as e:
            logger.error(f"DOCX解析失败 {file_path}: {e}")
            return ""
    
    def _table_to_text(self, table: List[List[str]]) -> str:
        """将表格转换为文本"""
        if not table:
            return ""
        
        text_lines = []
        for row in table:
            if row and any(cell for cell in row if cell):  # 过滤空行
                clean_row = [str(cell).strip() if cell else "" for cell in row]
                text_lines.append(" | ".join(clean_row))
        
        return "\n".join(text_lines)
    
    def extract_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        """提取文档元数据"""
        metadata = {
            'industries': [],
            'enterprise_scales': [],
            'policy_types': [],
            'requirements': [],
            'amounts': []
        }
        
        # 提取行业信息
        for industry, keywords in config.INDUSTRY_MAPPING.items():
            for keyword in keywords:
                if keyword in content:
                    metadata['industries'].append(industry)
                    break
        
        # 提取企业规模信息
        for scale, keywords in config.ENTERPRISE_SCALES.items():
            for keyword in keywords:
                if keyword in content:
                    metadata['enterprise_scales'].append(scale)
                    break
        
        # 提取政策类型
        for policy_type, keywords in config.POLICY_TYPES.items():
            for keyword in keywords:
                if keyword in content:
                    metadata['policy_types'].append(policy_type)
                    break
        
        # 提取金额信息
        amounts = self.money_pattern.findall(content)
        metadata['amounts'] = list(set(amounts))
        
        # 提取申请条件
        requirements = []
        sentences = re.split(r'[。！；\n]', content)
        for sentence in sentences:
            if self.requirement_pattern.search(sentence) and len(sentence) < 200:
                requirements.append(sentence.strip())
        
        metadata['requirements'] = requirements[:10]  # 限制数量
        
        return metadata
    
    def split_into_chunks(self, content: str, policy_id: str, tables: List[Dict] = None) -> List[PolicyChunk]:
        """将文档分割成块"""
        chunks = []
        
        # 按段落分割文本
        paragraphs = re.split(r'\n\s*\n', content)
        
        current_section = "开篇"
        chunk_id_counter = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para or len(para) < 10:
                continue
            
            # 检测是否为标题/章节
            if self.title_pattern.match(para) or self.section_pattern.match(para):
                current_section = para[:50]  # 取前50字符作为章节名
            
            # 将长段落进一步分割
            if len(para) > config.MAX_CHUNK_SIZE:
                sub_chunks = self._split_long_paragraph(para)
                for sub_chunk in sub_chunks:
                    chunk_id = f"{policy_id}_chunk_{chunk_id_counter}"
                    chunks.append(PolicyChunk(
                        chunk_id=chunk_id,
                        policy_id=policy_id,
                        content=sub_chunk,
                        section=current_section,
                        keywords=self._extract_keywords(sub_chunk)
                    ))
                    chunk_id_counter += 1
            else:
                chunk_id = f"{policy_id}_chunk_{chunk_id_counter}"
                chunks.append(PolicyChunk(
                    chunk_id=chunk_id,
                    policy_id=policy_id,
                    content=para,
                    section=current_section,
                    keywords=self._extract_keywords(para)
                ))
                chunk_id_counter += 1
        
        # 处理表格
        if tables:
            for i, table in enumerate(tables):
                chunk_id = f"{policy_id}_table_{i}"
                chunks.append(PolicyChunk(
                    chunk_id=chunk_id,
                    policy_id=policy_id,
                    content=table['text'],
                    chunk_type="table",
                    page_num=table['page'],
                    keywords=self._extract_keywords(table['text'])
                ))
        
        return chunks
    
    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """分割长段落"""
        sentences = re.split(r'[。！；]', paragraph)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_chunk + sentence) < config.MAX_CHUNK_SIZE:
                current_chunk += sentence + "。"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "。"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def generate_policy_id(self, file_path: str) -> str:
        """生成政策ID"""
        file_name = Path(file_path).stem
        # 使用文件名的hash作为ID的一部分
        hash_obj = hashlib.md5(file_name.encode('utf-8'))
        return f"policy_{hash_obj.hexdigest()[:8]}"
    
    def process_document(self, file_path: str) -> PolicyDocument:
        """处理单个文档"""
        logger.info(f"开始处理文档: {file_path}")
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            content, tables = self.extract_text_from_pdf(file_path)
        elif file_ext == '.docx':
            content = self.extract_text_from_docx(file_path)
            tables = []
        elif file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tables = []
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")
        
        if not content.strip():
            raise ValueError(f"文档内容为空: {file_path}")
        
        # 生成政策ID
        policy_id = self.generate_policy_id(file_path)
        
        # 提取标题（取文档开头的前100字符作为标题）
        title = content[:100].replace('\n', ' ').strip()
        if not title:
            title = Path(file_path).stem
        
        # 提取元数据
        metadata = self.extract_metadata(content, file_path)
        
        # 提取结构化字段
        structured_fields = self.extractor.extract_structured_fields(content)
        
        # 分割文档
        chunks = self.split_into_chunks(content, policy_id, tables)
        
        # 创建政策文档对象
        policy_doc = PolicyDocument(
            policy_id=policy_id,
            title=title,
            content=content,
            industry=metadata['industries'],
            enterprise_scale=metadata['enterprise_scales'],
            policy_type=metadata['policy_types'][0] if metadata['policy_types'] else None,
            file_path=file_path,
            chunks=chunks,
            # 🆕 添加用于数据库关联的字段
            original_filename=Path(file_path).name,  # 原始文件名（包含扩展名）
            document_number=structured_fields.get('document_number'),
            issuing_agency=structured_fields.get('issuing_agency')
        )
        
        logger.info(f"文档处理完成: {file_path}, 生成 {len(chunks)} 个分块")
        return policy_doc 