import yaml
import os
from utils.path_tool import get_abs_path
from datetime import datetime
from utils.logging_tool import logger
from langchain_core.documents import Document
from pypdf import PdfReader

def load_yaml_config(yaml_path :str ):
    if os.path.exists(get_abs_path(yaml_path)) :
        with open(yaml_path,"r",encoding= "utf-8") as f:
            return yaml.load(f,Loader=yaml.FullLoader)
    return None


def load_txt(dir :str) -> list[Document]:
    path = dir
    documents = []
    
    if os.path.isfile(path) and path.lower().endswith(".txt"):
      
        content = None

        try:
            with open(path, 'r', encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.error("打开文件失败")
        
        if content is None:
            raise ValueError(f"无法解码文件 {path}")
        
        if content.strip():
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
            
            doc = Document(
                page_content=content,
                metadata=metadata
            )
            documents.append(doc)
    
    return documents



def load_pdf(dir :str = "job/jobhunter.pdf") :
    
    path = get_abs_path(dir)
    documents = []
    
    if os.path.isfile(path) and path.lower().endswith(".pdf"):
        try:
            reader = PdfReader(path)
            
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    metadata = {
                        "source": path,
                        "file_name": os.path.basename(path),
                        "file_type": "pdf",
                        "page_number": page_num,
                        "total_pages": len(reader.pages),
                        "file_size": os.path.getsize(path),
                        "modified_time": datetime.fromtimestamp(
                            os.path.getmtime(path)
                        ).isoformat()
                    }
                    
                    # 添加 PDF 自带的元数据（如有）
                    if reader.metadata:
                        for key, value in reader.metadata.items():
                            metadata[f"pdf_{key}"] = value
                    
                    doc = Document(
                        page_content=text,
                        metadata=metadata
                    )
                    documents.append(doc)
                    
        except Exception as e:
            print(f"加载 PDF 文件 {path} 时出错: {e}")
    
    return documents