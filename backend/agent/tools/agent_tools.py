import sys
from pathlib import Path
from typing import Annotated

project_root = Path(__file__).resolve().parent.parent.parent

# 添加到 sys.path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 现在可以正常导入
from rag.ModelServer import JobServies, SummServer
from rag.ChromaServer import ChromaServer
from langchain.tools import tool
from utils.logging_tool import logger
from .tool_Servers import tool_registry


@tool_registry.register()
def get_job_working(user_id: Annotated[str, "当前用户的 user_id，必填，用于读取该用户的激活简历"] = None) -> str:
    """面试开始时调用：读取面试者简历，提取其意向岗位与意向城市。返回逗号分隔的岗位关键词，最后一个元素为意向城市，可作为 get_jd_content 的 key 入参（仅未选岗场景使用）。"""
    if not user_id:
        return "错误：需要提供 user_id 才能获取简历信息,模型无需重试"
    try:
        from utils.readyml_tool import load_resume
        user_resum = load_resume(int(user_id))

        if not user_resum:
            return "无简历信息，请先上传并激活简历,模型无需重试"

        resume_text = "\n".join([doc.page_content for doc in user_resum])
        resume_content = "简历内容如下:\n" + resume_text

        # [1] LLM 提取岗位关键词与意向城市
        content_str = JobServies.get_job(resume_text=resume_content)

        # [2] 爬虫 + 向量化存储逻辑暂时屏蔽（当前不需要存储 JD 数据）。
        # 爬虫与后台入库能力已迁移至 collectors/tools/zhaopin_scraper.py，如需恢复：
        #   from collectors.tools.zhaopin_scraper import ensure_bg_scrape
        #   city = content_str.split(',')[-1].strip()
        #   list_kwargs = [k.strip() for k in content_str.split(',')[:-1]]
        #   ensure_bg_scrape(city, list_kwargs)  # 缓存有效期内不重复爬取，后台线程爬取+摘要+写入向量库

        # 仅返回岗位关键词与城市，由模型自行决定是否继续调用 get_jd_content
        return content_str

    except (ValueError, TypeError):
        return f"错误：无效的 user_id {user_id},模型无需重试"
    except Exception as e:
        return f"错误：获取简历信息时发生异常 - {str(e)},模型无需重试"


@tool_registry.register()
def get_jd_content(
    user_id: Annotated[str, "当前用户的 user_id，必填"],
    key: Annotated[str, "岗位关键词：直接传入 get_job_working 的返回值（多个岗位用英文逗号分隔），必填"],
) -> str:
    """获取面试目标岗位的JD详情。面试开始阶段在 get_job_working 之后调用。优先返回用户已选择的目标岗位；未选岗时先在岗位库中按关键词匹配，未匹配到再回退向量库检索。"""
    # [1] 优先：当前面试会话所选的目标岗位 JD（新流程：以用户选定的 JD 为准）
    if user_id:
        try:
            from sqlClass.chat_session_model import ChatSessionModel
            from sqlClass.job_jd_model import JobJdModel

            session = ChatSessionModel().get_interviewing_with_jd(int(user_id))
            jd_id = session.get("selected_jd_id") if session else None
            if jd_id:
                jd = JobJdModel().get_by_id(int(jd_id))
                if not jd:
                    return "所选目标岗位JD不存在"
                content = "目标岗位JD信息如下:\n" + (jd.get("jd_content") or "")
                return SummServer(content, "SUMM_PROMPT").content
        except (ValueError, TypeError):
            return f"错误：无效的 user_id {user_id},模型无需重试"
        except Exception as e:
            logger.error(f"get_jd_content 获取所选JD失败: {e}")
            return f"错误：获取所选岗位JD时发生异常 - {str(e)},模型无需重试"

    if not key:
        # 引导模型补齐 key 重试，而不是放弃获取 JD
        return "未提供岗位关键词，请传入 key 参数（get_job_working 的返回值）后重试"

    # [2] 其次：按关键词在岗位库(job_jds)中匹配（本人数据优先，其次公用数据），命中则用该岗位的 JD 内容
    kws = [k.strip() for k in key.split(",") if k.strip()]
    try:
        from sqlClass.job_jd_model import JobJdModel

        rows = JobJdModel().search_choices(int(user_id), kws) if user_id else []
        if rows:
            # 关键词命中数最多者优先；并列时取 SQL 排序靠前者（本人数据优先、使用次数高者优先）
            def _hit_count(row):
                text = f"{row.get('job_name') or ''}{row.get('company_name') or ''}{row.get('keyword') or ''}"
                return sum(1 for kw in kws if kw in text)

            best = max(rows, key=_hit_count)
            jd_text = best.get("jd_content") or best.get("job_name") or ""
            head = (
                f"【匹配岗位】{best.get('job_name') or '未命名岗位'}"
                f"（{best.get('company_name') or '未知公司'}，"
                f"{best.get('city') or ''} {best.get('salary') or ''}）\n"
            )
            return head + SummServer("目标岗位JD信息如下:\n" + jd_text, "SUMM_PROMPT").content
    except Exception as e:
        logger.error(f"get_jd_content 检索岗位库失败: {e}")

    # [3] 兜底：岗位库无匹配时按关键词向量检索（兼容历史数据）
    content = ""
    for r in kws:
        content += f"{r} 的 JD 信息如下:\n"
        content_doc = ChromaServer().get_retriever().invoke(r)
        if not content_doc:
            content += "暂无相关JD信息。\n\n"
            continue
        for i, doc in enumerate(content_doc):
            content += f"JD 信息{i+1}:\n{doc.page_content}\n\n"
    return SummServer(content, "SUMM_PROMPT").content


@tool_registry.register()
def get_web_tutorial(key: Annotated[str, "用户关于本系统使用的提问内容"]) -> str:
    """返回本系统的网页操作教程（使用说明）。"""
    chroma = ChromaServer(chromaType="user_manual")
    results = chroma.chroma.similarity_search_with_score(key, k=3)
    if not results:
        return "未找到相关教程"
    docs = [(doc, score) for doc, score in results if score <= 0.5]
    if not docs:
        best_doc, best_score = results[0]
        return f"未找到完全匹配的教程，最接近的内容为:\n{best_doc.page_content}"
    return "\n\n".join(doc.page_content for doc, _ in docs)
