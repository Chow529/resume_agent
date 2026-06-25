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


"""
向量库存储,获取,读取
"""
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

        self.retriever = self.chroma.as_retriever(search_type="similarity_score_threshold",search_kwargs={'k': 5,"score_threshold":0.75})

    def get_retriever (self) ->VectorStoreRetriever:
        return self.retriever
    

    def StorageVector(self,content:str):
        """
        将文本存储到向量库内
        
        :param content: 文本信息
        :type content: str
        """
        pass


    def StorageMd5(self,md5:str):
        """
        存储md5值,将文本转化成md5值进行存储(去重使用)

        :param md5: 文本信息(转化成md5值)
        :type md5: str
        """
        pass


    def CheckMd5(self,content :str) ->bool:
        """
        检查文本转化成md5值是否存在,true存在 false不存在
        
        :param content: 说明
        :type content: str
        """
        return False


    def ChangeToMd5(self,content:str) ->str :
        """
        将长文本内容转化为固定的md5值
        
        :param content: 原文本内容
        :type content: str
        :return: 转换的md5值
        :rtype: str
        """
        return ""