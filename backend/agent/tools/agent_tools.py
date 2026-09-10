import sys
import json
import time
import threading
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
from utils.logging_tool import logger

# ========== 岗位爬取缓存 ==========
# 相同城市+关键词组合在有效期内不重复爬取
_JOB_CACHE_PATH = project_root / "backend" / "rag_knowladge" / "job_cache.json"
_JOB_CACHE_TTL = 86400  # 24 小时
_JOB_SCRAPE_TIME_BUDGET = 90  # 爬虫时间预算（秒），超时则使用已收集数据
_job_bg_lock = threading.Lock()
_job_bg_thread: threading.Thread | None = None


def _load_job_cache() -> dict:
    if _JOB_CACHE_PATH.is_file():
        try:
            return json.loads(_JOB_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_job_cache(cache: dict):
    _JOB_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _JOB_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def _cache_key(city: str, keywords: list) -> str:
    sorted_kw = sorted(keywords)
    return f"{city}|{'|'.join(sorted_kw)}"


def _bg_scrape_and_store(city: str, keywords: list, cache_key: str):
    """后台线程：爬取智联 JD + LLM 摘要 + 写入向量库（带时间预算兜底）"""
    global _job_bg_thread
    try:
        # 时间预算：爬虫最多执行 _JOB_SCRAPE_TIME_BUDGET 秒
        result = get_job_summary(city, keywords, output_filename=None, time_budget=_JOB_SCRAPE_TIME_BUDGET)
        jobs = result.get("jobs", [])
        if not jobs:
            logger.info("[后台] 爬虫未获取到 JD 数据")
            return
        content = SummServer(jobs, "CHROMA_PROMPT").content
        list_summ = [s for s in content.split('\n') if s.strip() and s.strip() != "none"]
        if list_summ:
            chroma = ChromaServer()
            chroma.batch_storage(list_summ)
        # 更新缓存
        cache = _load_job_cache()
        cache[cache_key] = int(time.time())
        _save_job_cache(cache)
        logger.info(f"[后台] JD 爬取+向量化完成，{len(list_summ)} 条摘要已入库")
    except Exception as e:
        logger.error(f"[后台] JD 爬取失败: {e}", exc_info=True)
    finally:
        with _job_bg_lock:
            _job_bg_thread = None


@tool(description="当一次面试开始时,首先会获取该面试者的简历,以获取面试者需要面试的岗位信息")
def get_job_working(user_id: str = None) -> str:
    """
    获取简历中的岗位信息
    user_id: 可选参数，指定用户ID。如果不传，则返回错误信息
    """
    if not user_id:
        return "错误：需要提供 user_id 才能获取简历信息,模型无需重试"
    try:
        from utils.readyml_tool import load_resume
        user_resum = load_resume(int(user_id))

        if not user_resum:
            return "无简历信息，请先上传并激活简历,模型无需重试"

        resume_text = "\n".join([doc.page_content for doc in user_resum])
        resume_content = "简历内容如下:\n" + resume_text

        # [1] LLM 提取岗位关键词
        content_str = JobServies.get_job(resume_text=resume_content)
        str_list = content_str.split(',')
        city = str_list[-1].strip()
        list_kwargs = [k.strip() for k in str_list[:-1]]

        # [2] 检查缓存：有效期内不重复爬取
        ck = _cache_key(city, list_kwargs)
        cache = _load_job_cache()
        cached_time = cache.get(ck, 0)
        cache_valid = (int(time.time()) - cached_time) < _JOB_CACHE_TTL

        if cache_valid:
            logger.info(f"[JD缓存] 命中缓存，跳过爬取: {ck}")
            return content_str

        # [3] 检查后台线程是否已在运行相同任务
        with _job_bg_lock:
            global _job_bg_thread
            if _job_bg_thread is not None and _job_bg_thread.is_alive():
                logger.info("[后台] 爬虫任务已在执行中，跳过")
                return content_str

            # [4] 启动后台线程
            _job_bg_thread = threading.Thread(
                target=_bg_scrape_and_store,
                args=(city, list_kwargs, ck),
                daemon=True,
            )
            _job_bg_thread.start()
            logger.info(f"[后台] 已启动爬虫任务: {ck}")

        return content_str + "\n[提示] 正在后台获取最新岗位JD数据，稍后查询即可获得更准确的面试内容。"

    except (ValueError, TypeError):
        return f"错误：无效的 user_id {user_id},模型无需重试"
    except Exception as e:
        return f"错误：获取简历信息时发生异常 - {str(e)},模型无需重试"


@tool(description="获取岗位JD信息")
def get_jd_content(key: str) -> str:
    result = key.split(",")
    content = ""
    output_content = ""
    for r in result:
        content += f"{r} 的 JD 信息如下:\n"
        content_doc = ChromaServer().get_retriever().invoke(r)
        if not content_doc:
            content += "暂无相关JD信息，岗位数据正在后台加载中，请稍后再试。\n\n"
            continue
        for i, doc in enumerate(content_doc):
            content += f"JD 信息{i+1}:\n{doc.page_content}\n\n"
    output_content = SummServer(content, "SUMM_PROMPT").content
    return output_content


@tool(description="返回网页操作教程")
def get_web_tutorial(key: str) -> str:
    chroma = ChromaServer(chromaType="user_manual")
    results = chroma.chroma.similarity_search_with_score(key, k=3)
    if not results:
        return "未找到相关教程"
    docs = [(doc, score) for doc, score in results if score <= 0.5]
    if not docs:
        best_doc, best_score = results[0]
        return f"未找到完全匹配的教程，最接近的内容为:\n{best_doc.page_content}"
    return "\n\n".join(doc.page_content for doc, _ in docs)
