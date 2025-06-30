import re
import fitz  # PyMuPDF
import pdfplumber
import docx2txt
import jieba
import hashlib
from typing import List, Dict, Any, Tuple
from pathlib import Path
import logging

from models import PolicyDocument, PolicyChunk
from config import config

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self):
        # 初始化jieba分词
        jieba.initialize()
        
        # 编译正则表达式
        self.title_pattern = re.compile(r'^[一二三四五六七八九十\d]+[、\.\s].*|第[一二三四五六七八九十\d]+[章节条款].*')
        self.section_pattern = re.compile(r'[（(][一二三四五六七八九十\d]+[)）].*')
        self.money_pattern = re.compile(r'[\d,，]+\s*万元|[\d,，]+\s*元|[\d,，]+\s*亿元')
        self.requirement_pattern = re.compile(r'应当|必须|需要|要求|条件|标准|规定')
        
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
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 使用jieba分词
        words = jieba.cut(text)
        
        # 过滤停用词和短词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没', '看', '好', '自己', '这', '那', '之', '与', '或', '等', '及'}
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        
        # 返回频次最高的关键词
        from collections import Counter
        word_freq = Counter(keywords)
        return [word for word, _ in word_freq.most_common(10)]
    
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
            chunks=chunks
        )
        
        logger.info(f"文档处理完成: {file_path}, 生成 {len(chunks)} 个分块")
        return policy_doc 