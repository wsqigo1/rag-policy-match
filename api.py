from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
import tempfile
from pathlib import Path

from models import QueryRequest, QueryResponse, SystemStatus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_policy_matcher():
    """获取policy_matcher实例"""
    from policy_matcher import policy_matcher
    return policy_matcher

# 创建FastAPI应用
app = FastAPI(
    title="政策匹配检索系统",
    description="基于RAG的政策文档智能匹配系统",
    version="1.0.0"
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
        "version": "1.0.0",
        "status": "运行中"
    }

@app.post("/search", response_model=QueryResponse)
async def search_policies(query_request: QueryRequest):
    """
    政策搜索接口
    
    Args:
        query_request: 查询请求对象
        
    Returns:
        查询响应结果
    """
    try:
        logger.info(f"收到查询请求: {query_request.query}")
        
        # 执行政策匹配
        policy_matcher = get_policy_matcher()
        response = policy_matcher.match_policies(query_request)
        
        logger.info(f"查询完成，返回 {response.total_results} 个结果")
        return response
        
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@app.get("/search/quick")
async def quick_search(
    q: str,
    industry: str = None,
    enterprise_scale: str = None,
    top_k: int = 10
):
    """
    快速查询接口（GET方式）
    
    Args:
        q: 查询文本
        industry: 行业筛选
        enterprise_scale: 企业规模
        top_k: 返回结果数量
        
    Returns:
        查询结果
    """
    try:
        query_request = QueryRequest(
            query=q,
            industry=industry,
            enterprise_scale=enterprise_scale,
            top_k=min(top_k, 50)  # 限制最大数量
        )
        
        policy_matcher = get_policy_matcher()
        response = policy_matcher.match_policies(query_request)
        return response
        
    except Exception as e:
        logger.error(f"快速查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

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

@app.get("/examples")
async def get_query_examples():
    """
    获取查询示例
    
    Returns:
        查询示例列表
    """
    examples = [
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
        },
        {
            "query": "新能源汽车产业有什么扶持政策",
            "description": "特定行业政策查询",
            "expected_results": "返回新能源汽车相关的产业扶持政策"
        },
        {
            "query": "人才引进有什么优惠政策",
            "description": "人才政策查询",
            "expected_results": "返回人才引进相关的政策和优惠措施"
        }
    ]
    
    return {"examples": examples}

@app.get("/categories")
async def get_policy_categories():
    """
    获取政策分类信息
    
    Returns:
        政策分类列表
    """
    from config import config
    
    categories = {
        "industries": list(config.INDUSTRY_MAPPING.keys()),
        "enterprise_scales": list(config.ENTERPRISE_SCALES.keys()),
        "policy_types": list(config.POLICY_TYPES.keys())
    }
    
    return categories

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
    uvicorn.run(app, host="0.0.0.0", port=8000) 