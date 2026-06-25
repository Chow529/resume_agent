from langchain.tools import tool
from rag.RagServer import JobServies,RagServer,SummServer

@tool(description="当一次面试开始时,首先会获取该面试者的简历,以获取面试者需要面试的岗位信息")
def get_job_working () -> str:
    return JobServies().get_job()

@tool(description="获取岗位JD信息")
def get_jd_content (key:str) -> str:
    result = key.split(",")
    content = ""
    
    for r in result :
        outputContent = ""
        content += f"{r}的JD信息如下:\n"
        content_doc = RagServer().get_retriever().invoke(r)
        for i, doc in enumerate(content_doc):
            content += f"JD信息{i+1}:\n{doc.page_content}\n\n"
        outputContent = SummServer(content).content
    return outputContent