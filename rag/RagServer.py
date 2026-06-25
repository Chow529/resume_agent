import sys
from pathlib import Path

# 获取当前文件所在目录的父目录（即项目根目录）
project_root = Path(__file__).parent.parent

# 将项目根目录添加到 sys.path 的最前面
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import os    
from utils.path_tool import get_abs_path             
from langchain_text_splitters import RecursiveCharacterTextSplitter
from model.MoelFactory import *
from utils.readyml_tool import load_yaml_config,load_txt,load_pdf
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever

class JobServies (object) :
    def __init__(self) -> None:
       
        prompt = load_yaml_config("prompt/prompt.yml")["RAG_PROMPT"] # type: ignore
        self.prompt_txt = prompt #jobhunter
        
        
        self.prompt = PromptTemplate.from_template(self.prompt_txt)
        self.chatmodel = ChatModelIni().InitModel()
        self.chain = self.prompt | self.chatmodel | StrOutputParser()


    def get_job (self) -> str:
        userResum = load_pdf()
        resume_content = userResum if len(userResum) else "无简历信息"
        return self.chain.invoke({"resume_content": resume_content})

class SummServer(object):
    def __init__(self,content : str) -> None:
       
        prompt = load_yaml_config("prompt/prompt.yml")["SUMM_PROMPT"] # type: ignore
        self.prompt_txt = prompt #jobhunter

        self.prompt = PromptTemplate.from_template(self.prompt_txt)
        self.chatmodel = ChatModelIni().InitModel()
        self.chain = self.prompt | self.chatmodel | StrOutputParser()
        
        self.content = self._get_content(content)


    def _get_content (self,content: str) ->str:
        return self.chain.invoke({"input":content})


class RagServer (object):
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

if __name__ == "__main__":
    res = JobServies().get_job()
    print(res)