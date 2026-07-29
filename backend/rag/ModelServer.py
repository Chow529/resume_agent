import sys
from pathlib import Path

# 获取当前文件所在目录的父目录（即项目根目录）
project_root = Path(__file__).parent.parent

# 将项目根目录添加到 sys.path 的最前面
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

              
from model.MoelFactory import ChatModelIni
from utils.readyml_tool import load_yaml_config,load_txt,load_pdf
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

class JobServies (object) :
    def __init__(self) -> None:      
        prompt = load_yaml_config("prompt/prompt.yml")["RAG_PROMPT"] # type: ignore
        self.prompt_txt = prompt #jobhunter
        
        
        self.prompt = PromptTemplate.from_template(self.prompt_txt)
        self.chatmodel = ChatModelIni().InitModel()
        self.chain = self.prompt | self.chatmodel | StrOutputParser()


    def get_job (self) -> str:
        userResum = load_pdf()
        resume_content = "简历内容如下:\n"
        if len(userResum) :
            for ctn in userResum :
                resume_content += ctn.page_content
        else : 
            resume_content += "无简历信息"

        return self.chain.invoke({"resume_content": resume_content})

class SummServer:
    def __init__(self,content : str,porompt : str) -> None:
        """
        content : 文本信息
        porompt : 提示词
        """

        prompt = load_yaml_config("prompt/prompt.yml")[porompt] # type: ignore
        self.prompt_txt = prompt       #jobhunter

        self.prompt = PromptTemplate.from_template(self.prompt_txt)
        self.chatmodel = ChatModelIni().InitModel()
        self.chain = self.prompt | self.chatmodel | StrOutputParser()
        
        self._content = self.__get_content(content)


    def __get_content (self,content: str) ->str:
        return self.chain.invoke({"input":content})
    
    @property
    def content (self) -> str:
        return self._content




if __name__ == "__main__":
    res = JobServies().get_job()
    print(res)