import sys
from pathlib import Path
from typing import Optional
from pathlib import Path

# 获取当前文件所在目录的父目录（即项目根目录）
project_root = Path(__file__).parent.parent

# 将项目根目录添加到 sys.path 的最前面
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


from model.MoelFactory import ChatModelIni
from utils.readyml_tool import load_yaml_config, load_txt
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

class JobServies(object):
    def __init__(self) -> None:
        prompt = load_yaml_config("prompt/prompt.yml")["RAG_PROMPT"]  # type: ignore
        self.prompt_txt = prompt

        self.prompt = PromptTemplate.from_template(self.prompt_txt)
        self.chatmodel = ChatModelIni().InitModel()
        self.chain = self.prompt | self.chatmodel | StrOutputParser()

    @classmethod
    def get_job(cls, resume_text: str = None, user_id: Optional[int] = None) -> str:
        """
        获取简历内容生成的 job 信息

        Args:
            resume_text: 可选的简历文本内容。如果传入，直接使用
            user_id: 用户ID，用于从 user_resumes 表获取该用户的激活简历

        Returns:
            处理后的简历字符串（包含城市、关键词等信息）
        """
        resume_content = ""

        if resume_text and resume_text.strip():
            # 直接使用传入的文本
            resume_content = "简历内容如下:\n" + resume_text
        else:
            # 仅通过 user_id 获取用户专属简历，不回退到默认 PDF
            if user_id is not None:
                from utils.readyml_tool import load_resume
                userResum = load_resume(user_id)
                if userResum:
                    resume_content = "简历内容如下:\n" + "\n".join([ctn.page_content for ctn in userResum])
                else:
                    resume_content = "无简历信息，请先上传并激活简历"
            else:
                resume_content = "未提供 user_id，无法获取用户简历"
        return cls().chain.invoke({"resume_content": resume_content})


class SummServer:
    def __init__(self, content: str, prompt_type: str) -> None:
        """
        content : 文本信息
        prompt_type : 提示词类型（如 "SUMM_PROMPT"）
        """
        prompt = load_yaml_config("prompt/prompt.yml")[prompt_type]  # type: ignore
        self.prompt_txt = prompt

        self.prompt = PromptTemplate.from_template(self.prompt_txt)
        self.chatmodel = ChatModelIni().InitModel()
        self.chain = self.prompt | self.chatmodel | StrOutputParser()

        self._content = self.__get_content(content)


    def __get_content(self, content: str) -> str:
        return self.chain.invoke({"input": content})

    @property
    def content(self) -> str:
        return self._content


if __name__ == "__main__":
    res = JobServies().get_job()
    print(res)
