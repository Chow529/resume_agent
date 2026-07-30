import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent

# 添加到 sys.path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 现在可以正常导入
from rag.ModelServer import JobServies, SummServer
from rag.ChromaServer import ChromaServer
from .zhaopin_scraper import get_job_summary
from langchain.tools import tool


@tool(description="当一次面试开始时,首先会获取该面试者的简历,以获取面试者需要面试的岗位信息")
def get_job_working() -> str:
    """
    获取简历中的岗位信息
    简历文本由系统在 /start 时通过线程上下文传入，无需手动指定
    """
    # 从线程上下文读取当前会话的简历文本
    from utils.session_context import get_current_session
    ctx = get_current_session()
    resume_text = ctx.get("resume_text", "")

    # 通过 JobServies 获取岗位信息
    if resume_text and resume_text.strip():
        contentStr = JobServies().get_job(resume_text=resume_text)
    else:
        # 从默认路径加载 PDF（向后兼容）
        from utils.readyml_tool import load_pdf
        userResum = load_pdf()
        fallback_text = "简历内容如下:\n"
        if userResum:
            for ctn in userResum:
                fallback_text += ctn.page_content
        else:
            fallback_text += "无简历信息"
        contentStr = JobServies().get_job(resume_text=fallback_text)

    strList = contentStr.split(',')
    city = strList[-1]
    listKwargs = strList[:-1]

    try:
        result = get_job_summary(city, listKwargs, output_filename=None)
    except Exception as e:
        print(f"[警告] 智联招聘爬取失败: {e}, 继续执行后续流程")
        result = {"jobs": []}

    content = SummServer(result["jobs"], "CHROMA_PROMPT").content

    listSumm = content.split('\n')

    chroma = ChromaServer()
    for summ in listSumm:
        if summ.strip() != "none":
            chroma.StorageVector(summ)

    return contentStr


@tool(description="获取岗位JD信息")
def get_jd_content(key: str) -> str:
    result = key.split(",")
    content = ""

    for r in result:
        outputContent = ""
        content += f"{r} 的 JD 信息如下:\n"
        content_doc = ChromaServer().get_retriever().invoke(r)
        for i, doc in enumerate(content_doc):
            content += f"JD 信息{i+1}:\n{doc.page_content}\n\n"
    outputContent = SummServer(content, "SUMM_PROMPT").content
    return outputContent


@tool(description="返回网页操作教程")
def get_web_tutorial(key: str) -> str:
    return ""
# if __name__ == "__main__" :
#     name = get_job_working()
#     print(name)
