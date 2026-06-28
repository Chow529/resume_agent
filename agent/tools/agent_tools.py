from langchain.tools import tool
from rag.ModelServer import JobServies,SummServer
from rag.ChromaServer import ChromaServer
from  zhaopin_scraper import get_job_summary

@tool(description="当一次面试开始时,首先会获取该面试者的简历,以获取面试者需要面试的岗位信息")
def get_job_working () -> str:
    #todo 进行存储向量库了id为职位的名称
    strlist = JobServies().get_job()

    city = strlist[-1]
    listKwargs = strlist[:-1]


    content = SummServer(get_job_summary(city,listKwargs)["jobs"],"CHROMA_PROMPT").content

    listSumm = content.split('\n')
    
    return strlist

@tool(description="获取岗位JD信息")
def get_jd_content (key:str) -> str:
    result = key.split(",")
    content = ""
    
    for r in result :
        outputContent = ""
        content += f"{r}的JD信息如下:\n"
        content_doc = ChromaServer().get_retriever().invoke(r)
        for i, doc in enumerate(content_doc):
            content += f"JD信息{i+1}:\n{doc.page_content}\n\n"
    outputContent = SummServer(content,"SUMM_PROMPT").content
    return outputContent
