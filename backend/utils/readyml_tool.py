import yaml
import os
from datetime import datetime
from typing import List

from utils.path_tool import get_abs_path
from utils.logging_tool import logger
from langchain_core.documents import Document
from markitdown import MarkItDown


def load_yaml_config(yaml_path: str):
    """加载 YAML 配置文件"""
    if os.path.exists(get_abs_path(yaml_path)):
        with open(get_abs_path(yaml_path), "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=yaml.FullLoader)
    return None


def load_txt(dir: str) -> List[Document]:
    """从 TXT 文件创建 Document 列表"""
    path = get_abs_path(dir)
    documents = []

    if os.path.isfile(path) and path.lower().endswith(".txt"):
        try:
            with open(path, 'r', encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.error(f"打开文件失败: {path}")
            return []

        if content and content.strip():
            metadata = {
                "source": path,
                "file_name": os.path.basename(path),
                "file_type": "txt",
                "file_size": os.path.getsize(path),
                "modified_time": datetime.fromtimestamp(
                    os.path.getmtime(path)
                ).isoformat(),
                "encoding": "utf-8"
            }
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)

    return documents


def load_resume(file_path: str) -> List[Document]:
    """
    使用 markitdown 统一读取 PDF / DOCX
    返回 Document 列表
    """
    abs_path = get_abs_path(file_path) if not os.path.isabs(file_path) else file_path

    if not os.path.isfile(abs_path):
        logger.error(f"文件不存在: {abs_path}")
        return []

    ext = os.path.splitext(abs_path)[1].lower()
    if ext not in ('.pdf', '.docx'):
        logger.error(f"不支持的文件格式: {ext}")
        return []

    try:
        md = MarkItDown()
        result = md.convert_local(abs_path)
        text_content = result.text_content if result else ""

        if text_content and text_content.strip():
            metadata = {
                "source": abs_path,
                "file_name": os.path.basename(abs_path),
                "file_type": ext.lstrip('.'),
                "file_size": os.path.getsize(abs_path),
                "modified_time": datetime.fromtimestamp(
                    os.path.getmtime(abs_path)
                ).isoformat()
            }
            doc = Document(page_content=text_content, metadata=metadata)
            return [doc]
    except Exception as e:
        logger.error(f"加载文件 {abs_path} 时出错: {e}")

    return []


# ===== 向后兼容函数（供旧代码 /start fallback 使用） =====

def load_pdf(dir: str = "job/jobhunter.pdf") -> List[Document]:
    """向后兼容：默认读取 job/jobhunter.pdf"""
    return load_resume(dir)
