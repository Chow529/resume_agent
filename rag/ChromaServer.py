import sys
from pathlib import Path

# 获取当前文件所在目录的父目录（即项目根目录）
project_root = Path(__file__).parent.parent

# 将项目根目录添加到 sys.path 的最前面
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path  
import os  
from model.MoelFactory import EmbeddingModelIni

class ChromaServer (object):
    def __init__(self) -> None:
        path = get_abs_path("rag_knowladge")
        if not os.path.exists(path) :
            os.makedirs(path)

        self.chroma = Chroma(
            collection_name="job_jd",
            embedding_function= EmbeddingModelIni().InitModel(),
            persist_directory= path
        )

        self.spliter = RecursiveCharacterTextSplitter(
            separators=["\n\n","\n",""],
            chunk_size=600,
            chunk_overlap=100,
            length_function=len
        )

        self.retriever = self.chroma.as_retriever(search_kwargs={'k': 5})

    def get_retriever (self) ->VectorStoreRetriever:
        return self.retriever