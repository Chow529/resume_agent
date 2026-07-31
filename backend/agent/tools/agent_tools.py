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
def get_job_working(user_id: str = None) -> str:
    """
    获取简历中的岗位信息
    user_id: 可选参数，指定用户ID。如果不传，则返回错误信息
    """
    # 如果没有提供 user_id，返回错误
    if not user_id:
        return "错误：需要提供 user_id 才能获取简历信息"
    # print(f"user_id: {user_id}")
    try:
        from utils.readyml_tool import load_resume
        userResum = load_resume(int(user_id))

        if not userResum:
            return "无简历信息，请先上传并激活简历"

        resume_text = "\n".join([doc.page_content for doc in userResum])
        resume_content = "简历内容如下:\n" + resume_text
        # print(f"简历内容: {resume_content}")
        # 通过 JobServies 获取岗位信息
        contentStr = JobServies.get_job(resume_text=resume_content)
        # print(f"岗位信息: {contentStr}")
        strList = contentStr.split(',')
        city = strList[-1]
        listKwargs = strList[:-1]

        try:
            result = get_job_summary(city, listKwargs, output_filename=None)
        except Exception as e:
            print(f"[警告] 智联招聘爬取失败: {e}, 继续执行后续流程")
            result = {"jobs": []}
        # print(result)
        content = SummServer(result["jobs"], "CHROMA_PROMPT").content
        listSumm :list[str] = content.split('\n')
        

        if len(listSumm) > 0:
            chroma = ChromaServer()
            for summ in listSumm:
                if summ.strip() != "none":
                    chroma.StorageVector(summ)
        return contentStr

    except (ValueError, TypeError) as e:
        return f"错误：无效的 user_id {user_id}"
    except Exception as e:
        return f"错误：获取简历信息时发生异常 - {str(e)}"


@tool(description="获取岗位JD信息")
def get_jd_content(key: str) -> str:
    result = key.split(",")
    # print(f"[get_jd_content] 获取的岗位关键字: {result}")
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
