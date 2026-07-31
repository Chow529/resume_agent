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


def load_resume(user_id: int = None) -> List[Document]:
    """
    获取用户简历内容（从 database user_resumes 表）
    - 如果传入 user_id，从 user_resumes 表获取该用户激活的简历
    - 优先使用 resume_text（markitdown 解析后的文本），其次回退到 file_path（原始文件路径）
    - 如果未传入 user_id 或没有激活简历，返回空列表
    """
    if user_id is None:
        return []

    try:
        from sqlClass.resume_model import ResumeModel
        resume_model = ResumeModel()
        active_resume = resume_model.get_active(user_id)

        if active_resume:
            # 优先使用 resume_text（解析后的文本）
            if active_resume.get('resume_text') and active_resume['resume_text'].strip():
                content = active_resume['resume_text']
            elif active_resume.get('file_path'):
                # 回退到原始文件路径，需要读取文件
                file_path = active_resume['file_path']
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ('.pdf', '.docx'):
                        md = MarkItDown()
                        result = md.convert_local(file_path)
                        content = result.text_content if result else ""
                        if not content or not content.strip():
                            content = "无法解析文件内容"
                    else:
                        content = "不支持的文件格式"
                else:
                    content = f"文件不存在: {file_path}"
            else:
                content = "无简历内容"

            doc = Document(
                page_content=content,
                metadata={
                    'source': 'user_resume',
                    'file_name': active_resume.get('filename', ''),
                    'file_type': 'user_resume',
                    'user_id': user_id,
                    'uploaded_at': active_resume.get('uploaded_at', '')
                }
            )
            return [doc]
    except Exception as e:
        logger.error(f"加载用户 {user_id} 简历时出错: {e}")

    return []


# ===== 向后兼容函数（供旧代码 /start fallback 使用） =====

# def load_pdf(dir: str = "job/jobhunter.pdf") -> List[Document]:
#     """向后兼容：默认读取 job/jobhunter.pdf"""
#     return load_resume(dir)
