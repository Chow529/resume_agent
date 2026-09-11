"""
智联招聘爬虫 - 支持自定义地区和关键词
使用 curl_cffi 模拟 Chrome TLS 指纹绕过反爬
输出 CSV 文件

除爬取接口外，还包含岗位爬取缓存与后台「爬取+摘要+向量化入库」逻辑
（供 agent 工具与采集模块复用）。
"""
import csv
import json
import re
import time
import os
import threading
from html import unescape
from pathlib import Path
from datetime import datetime
from curl_cffi import requests

# ========== 配置 ==========
# 城市代码映射（智联招聘）
CITY_CODE_MAP = {
    "北京": "530",
    "上海": "538",
    "广州": "619",
    "深圳": "765",
    "杭州": "653",
    "成都": "801",
    "武汉": "736",
    "南京": "635",
    "西安": "854",
    "重庆": "806",
    "天津": "531",
    "苏州": "639",
    "厦门": "604",
    "长沙": "749",
    "郑州": "725",
    "青岛": "715",
    "大连": "546",
    "沈阳": "547",
    "长春": "512",
    "哈尔滨": "552",
    "石家庄": "515",
    "济南": "696",
    "合肥": "662",
    "福州": "598",
    "昆明": "702",
    "贵阳": "700",
    "南昌": "670",
    "南宁": "728",
    "兰州": "710",
    "乌鲁木齐": "758",
    "呼和浩特": "584",
    "银川": "764",
    "西宁": "848",
    "拉萨": "705",
    "香港": "590",
    "澳门": "808",
    "台湾": "741",
}

PAGE_SIZE = 20
REQUEST_DELAY = 2       # 请求间隔（秒），避免反爬

# 岗位详情抓取（列表页只有截断的 jobDescription，完整「岗位职责/任职要求」在详情页）
DETAIL_FETCH_LIMIT = 30          # 单次最多抓取多少条岗位详情
DETAIL_FETCH_CONCURRENCY = 5     # 详情页并发数
DETAIL_FETCH_TIME_BUDGET = 60    # 详情抓取时间预算（秒），超时用已抓到的数据

# 详情缺失时的兜底文案（保证「岗位职责」字段非空，面试有据可依）
_JD_FALLBACK_TEMPLATE = (
    "招聘方未提供详细岗位职责描述，面试将围绕岗位名称、技能要求"
    "{skills}及相关项目经验展开。"
)


def _resolve_ca_bundle():
    """返回可用于 TLS 校验的 CA 文件路径。

    libcurl(Windows) 无法加载含非 ASCII 字符的路径（本项目虚拟环境路径含中文，
    会报 "error setting certificate verify locations"），此时把 certifi 证书复制到
    ASCII 临时目录后再使用；异常时回退 True（交由底层默认处理）。
    """
    try:
        import shutil
        import tempfile
        import certifi

        path = certifi.where()
        if path.isascii():
            return path
        dst = Path(tempfile.gettempdir()) / "zhaopin_cacert.pem"
        if not dst.is_file():
            shutil.copyfile(path, dst)
        return str(dst)
    except Exception:
        return True


_CA_BUNDLE = _resolve_ca_bundle()


def extract_state_from_html(html: str) -> dict:
    """从 HTML 中提取 __INITIAL_STATE__ JSON 数据"""
    idx = html.find("__INITIAL_STATE__")
    if idx == -1:
        return {}
    script_close = html.find("</script>", idx)
    if script_close == -1:
        return {}
    eq_idx = html.find("=", idx)
    json_start = html.find("{", eq_idx)
    json_str = html[json_start:script_close].rstrip().rstrip(";").strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {}


def search_jobs(keyword: str, city_code: str, page: int = 1) -> dict:
    """搜索职位，返回 __INITIAL_STATE__ 数据"""
    session = requests.Session()
    params = {
        "kw": keyword,
        "jl": city_code,
        "p": str(page),
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        r = session.get(
            "https://sou.zhaopin.com/",
            params=params,
            headers=headers,
            impersonate="chrome120",
            timeout=10,
            verify=_CA_BUNDLE,
        )
        return extract_state_from_html(r.text)
    except Exception as e:
        print(f"  [错误] 搜索 '{keyword}' 第{page}页失败: {e}")
        return {}


def parse_job(pos: dict) -> dict:
    """解析单个职位数据"""
    # 解析技能标签
    skill_tags = pos.get("jobSkillTags", [])
    skills = ", ".join([t.get("name", "") for t in skill_tags]) if skill_tags else ""

    # 解析福利
    welfare = pos.get("welfareLabel", [])
    welfare_str = ", ".join(welfare) if welfare else ""

    # 解析商业标签
    commercial = pos.get("commercialLabel", [])
    commercial_str = ", ".join(
        [c.get("typeName", "") for c in commercial]
    ) if commercial else ""

    # 获取职位详情页 URL
    position_url = pos.get("positionURL", "")
    if position_url and not position_url.startswith("http"):
        position_url = "https:" + position_url if position_url.startswith("//") else "https://www.zhaopin.com" + position_url

    return {
        "职位名称": pos.get("name", ""),
        "公司名称": pos.get("companyName", ""),
        "薪资": pos.get("salary60", ""),
        "城市": pos.get("workCity", ""),
        "区域": pos.get("cityDistrict", ""),
        "学历要求": pos.get("education", ""),
        "经验要求": pos.get("workingExp", ""),
        "公司规模": pos.get("companySize", ""),
        "公司行业": pos.get("industryName", ""),
        "融资阶段": pos.get("financingStage", "") or "",
        "技能标签": skills,
        "福利": welfare_str,
        "标签": commercial_str,
        "招聘人数": pos.get("recruitNumber", ""),
        "职位类型": pos.get("workType", ""),
        "发布日期": pos.get("publishTime", ""),
        # 列表页自带的职位描述（约 70 字截断预览），仅作详情抓取失败时的兜底
        "职位描述": pos.get("jobDescription", "") or "",
        "职位URL": position_url,
        "公司URL": pos.get("companyUrl", ""),
        "搜索关键词": "",  # 后续填充
    }


def _html_to_text(text: str) -> str:
    """把 JD 描述中的 HTML 片段转为纯文本（保留换行）"""
    if not text:
        return ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|tr|h[1-6])>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def fetch_job_detail(url: str) -> str:
    """抓取岗位详情页，返回完整 JD 文本（含岗位职责/任职要求）；失败返回空串"""
    if not url:
        return ""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, impersonate="chrome120", timeout=15, verify=_CA_BUNDLE)
        if r.status_code != 200:
            return ""
        state = extract_state_from_html(r.text)
        position = (state.get("jobDetail") or {}).get("detailedPosition") or {}
        # description 通常为纯文本，个别岗位带 HTML；jobDesc 为 <br> 分隔的 HTML
        return _html_to_text(position.get("description") or "") or _html_to_text(position.get("jobDesc") or "")
    except Exception as e:
        print(f"  [详情] 抓取失败 {url}: {e}")
        return ""


def _ensure_description(job: dict) -> dict:
    """保证每条岗位的「职位描述」非空：详情 > 列表预览 > 结构化字段兜底"""
    desc = (job.get("职位描述") or "").strip()
    if not desc:
        skills = (job.get("技能标签") or "").strip()
        desc = _JD_FALLBACK_TEMPLATE.format(skills=f"（{skills}）" if skills else "")
    job["职位描述"] = desc
    return job


def enrich_jobs_with_detail(
    jobs: list,
    limit: int = None,
    concurrency: int = None,
    time_budget: int = None,
    on_progress=None,
) -> list:
    """为岗位补充完整 JD：并发抓详情页覆盖「职位描述」，失败保留列表预览，最后统一兜底

    Args:
        jobs: parse_job 产出的岗位列表（原地修改并返回）
        limit: 最多抓取多少条详情（默认 DETAIL_FETCH_LIMIT）
        concurrency: 并发数（默认 DETAIL_FETCH_CONCURRENCY）
        time_budget: 时间预算秒（默认 DETAIL_FETCH_TIME_BUDGET）
        on_progress: 可选进度回调 on_progress("详情", done, done, total)
    """
    limit = DETAIL_FETCH_LIMIT if limit is None else limit
    concurrency = DETAIL_FETCH_CONCURRENCY if concurrency is None else concurrency
    time_budget = DETAIL_FETCH_TIME_BUDGET if time_budget is None else time_budget

    targets = [j for j in jobs if j.get("职位URL")][:limit]
    if targets:
        from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout

        total = len(targets)
        done = 0
        pool = ThreadPoolExecutor(max_workers=concurrency)
        futures = {pool.submit(fetch_job_detail, j["职位URL"]): j for j in targets}
        try:
            for fut in as_completed(futures, timeout=time_budget):
                job = futures[fut]
                try:
                    desc = (fut.result() or "").strip()
                except Exception:
                    desc = ""
                if desc:
                    job["职位描述"] = desc
                done += 1
                if on_progress:
                    try:
                        on_progress("详情", done, done, total)
                    except Exception:
                        pass
        except FuturesTimeout:
            print(f"  ⏰ 详情抓取超过预算 {time_budget}s，已抓取 {done}/{total} 条")
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        print(f"  📄 岗位详情抓取完成：{done}/{total} 条")

    # 统一兜底，保证「职位描述」字段都有内容
    for j in jobs:
        _ensure_description(j)
    return jobs


def scrape_all(city_name: str, keywords: list, time_budget: int = 60, on_progress=None, with_detail: bool = True) -> list:
    """
    主爬取逻辑

    Args:
        city_name: 城市名称，如 "成都"
        keywords: 搜索关键词列表，如 ["AI智能体", "AI Agent"]
        time_budget: 爬取时间预算（秒），超时立即返回已收集的数据
        on_progress: 可选进度回调 on_progress(keyword, page, collected, total_pages)，
            每处理完一页调用一次，不影响原有爬取逻辑
        with_detail: 是否抓取岗位详情页补充完整 JD（岗位职责/任职要求）

    Returns:
        list: 职位数据列表
    """
    # 获取城市代码
    city_code = CITY_CODE_MAP.get(city_name)
    if not city_code:
        print(f"❌ 错误：不支持的城市 '{city_name}'")
        print(f"   支持的城市列表: {', '.join(CITY_CODE_MAP.keys())}")
        return []

    start_time = time.time()
    all_jobs = {}  # 用 jobId 去重
    total_pages = 0
    total_positions = 0

    def _notify(keyword: str, page: int, pages: int):
        if on_progress:
            try:
                on_progress(keyword, page, len(all_jobs), pages)
            except Exception:
                pass

    for keyword in keywords:
        # 时间预算检查：超时则停止爬取，返回已收集数据
        if time.time() - start_time > time_budget:
            print(f"⏰ 爬取时间超过预算 {time_budget}s，提前结束，已收集 {len(all_jobs)} 条数据")
            break

        print(f"\n{'='*60}")
        print(f"搜索关键词: {keyword}")
        print(f"{'='*60}")

        # 先获取第一页，确定总页数
        state = search_jobs(keyword, city_code, page=1)
        if not state:
            print(f"  ⚠️ 未获取到数据，跳过该关键词")
            continue

        position_count = state.get("positionCount", 0)
        pages = state.get("pages", 1)

        # 处理第一页
        for pos in state.get("positionList", []):
            job_id = pos.get("jobId") or pos.get("number") or pos.get("uuid")
            if job_id and job_id not in all_jobs:
                parsed = parse_job(pos)
                parsed["搜索关键词"] = keyword
                parsed["职位ID"] = str(job_id)
                all_jobs[job_id] = parsed

        total_pages += pages
        total_positions += position_count
        _notify(keyword, 1, pages)

        # 获取后续页面
        for page in range(2, pages + 1):
            # 时间预算检查：超时则停止爬取
            if time.time() - start_time > time_budget:
                print(f"⏰ 爬取时间超过预算 {time_budget}s，提前结束，已收集 {len(all_jobs)} 条数据")
                break
            time.sleep(REQUEST_DELAY)
            state = search_jobs(keyword, city_code, page=page)
            if not state:
                continue
            for pos in state.get("positionList", []):
                job_id = pos.get("jobId") or pos.get("number") or pos.get("uuid")
                if job_id and job_id not in all_jobs:
                    parsed = parse_job(pos)
                    parsed["搜索关键词"] = keyword
                    parsed["职位ID"] = str(job_id)
                    all_jobs[job_id] = parsed
            _notify(keyword, page, pages)

        time.sleep(REQUEST_DELAY)

    jobs = list(all_jobs.values())

    # 抓取岗位详情页，补全「岗位职责/任职要求」（列表页只有截断预览）
    if with_detail and jobs:
        print(f"\n{'='*60}")
        print(f"📄 抓取岗位详情（最多 {DETAIL_FETCH_LIMIT} 条，预算 {DETAIL_FETCH_TIME_BUDGET}s）")
        print(f"{'='*60}")
        enrich_jobs_with_detail(jobs, on_progress=on_progress)
    else:
        for j in jobs:
            _ensure_description(j)

    return jobs


def save_csv(jobs: list, filename: str):
    """保存为 CSV 文件"""
    if not jobs:
        print("⚠️ 没有数据可保存！")
        return

    fieldnames = [
        "职位名称", "公司名称", "薪资", "城市", "区域",
        "学历要求", "经验要求", "公司规模", "公司行业",
        "融资阶段", "技能标签", "福利", "标签",
        "招聘人数", "职位类型", "发布日期",
        "职位URL", "公司URL", "搜索关键词",
    ]

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs)

    # print(f"💾 CSV 已保存到: {filename}")
    # print(f"📊 共 {len(jobs)} 条职位数据")


def get_job_summary(city_name: str, keywords: list, output_filename: str = None, time_budget: int = 60, on_progress=None, with_detail: bool = True):
    """
    灵活的任务总结函数

    Args:
        city_name: 城市名称（中文），如 "成都"
        keywords: 搜索关键词列表，如 ["AI智能体", "AI Agent", "大模型 agent"]
        output_filename: 输出文件名（可选），如不指定则自动生成
        time_budget: 爬取时间预算（秒），默认 60 秒，超时使用已收集数据
        on_progress: 可选进度回调 on_progress(keyword, page, collected, total_pages)
        with_detail: 是否抓取岗位详情页补充完整 JD（岗位职责/任职要求）

    Returns:
        dict: 包含职位列表和统计信息的字典
    """
    # 自动生成输出文件名
    if output_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{city_name}_{'_'.join(keywords[:3])}_智联招聘_{timestamp}.csv"
        # 如果关键词太长，截断
        if len(output_filename) > 100:
            output_filename = f"{city_name}_AI岗位_智联招聘_{timestamp}.csv"
    
    print("=" * 70)
    print(f"🚀 智联招聘爬虫")
    print(f"📍 城市: {city_name}")
    print(f"🔍 搜索关键词: {', '.join(keywords)}")
    # print(f"📁 输出文件: {output_filename}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 爬取数据 (静默模式,不打印进度)
    jobs = scrape_all(city_name, keywords, time_budget=time_budget, on_progress=on_progress, with_detail=with_detail)

    if not jobs:
        return {"jobs": [], "stats": {}}

    # 保存 CSV
    output_path = os.path.join(os.path.dirname(__file__), output_filename)
    # save_csv(jobs, output_path)

    # 统计分析 (静默模式)
    # print(f"\n{'='*70}")
    # print("📈 统计分析")
    # print("=" * 70)

    # 1. 总体统计
    companies = set(j.get("公司名称", "") for j in jobs if j.get("公司名称"))
    # print(f"\n📊 总体统计:")
    # print(f"  - 去重后职位数: {len(jobs)}")
    # print(f"  - 涉及公司数: {len(companies)}")

    # 2. 薪资分布
    salary_levels = {"10K以下": 0, "10K-20K": 0, "20K-30K": 0, "30K-50K": 0, "50K以上": 0, "面议": 0, "实习": 0}
    salary_list = []
    for j in jobs:
        s = j.get("薪资", "")
        if "天" in s or "元/天" in s:
            salary_levels["实习"] += 1
        elif "面议" in s or not s:
            salary_levels["面议"] += 1
        else:
            nums = re.findall(r"[\d.]+", s.replace("万", "0000").replace("千", "000"))
            if nums:
                try:
                    # 取薪资范围的最大值
                    max_salary = float(nums[-1])
                    if "万" in s:
                        max_salary *= 10000
                    elif "千" in s:
                        max_salary *= 1000
                    salary_list.append(max_salary)
                    if max_salary < 10000:
                        salary_levels["10K以下"] += 1
                    elif max_salary < 20000:
                        salary_levels["10K-20K"] += 1
                    elif max_salary < 30000:
                        salary_levels["20K-30K"] += 1
                    elif max_salary < 50000:
                        salary_levels["30K-50K"] += 1
                    else:
                        salary_levels["50K以上"] += 1
                except ValueError:
                    salary_levels["面议"] += 1
            else:
                salary_levels["面议"] += 1

    # print(f"\n💰 薪资分布:")
    # for level, count in salary_levels.items():
    #     if count > 0:
    #         print(f"  - {level}: {count} 个 ({count/len(jobs)*100:.1f}%)")

    # 计算平均薪资（仅统计有明确薪资的）
    avg_salary = None
    if salary_list:
        avg_salary = sum(salary_list) / len(salary_list)
        # print(f"\n  📊 平均薪资（有明确薪资的岗位）: {avg_salary/10000:.1f}K/月")
        # print(f"  💰 最高薪资: {max(salary_list)/10000:.1f}K/月")
        # print(f"  💰 最低薪资: {min(salary_list)/10000:.1f}K/月")

    # 3. 学历要求分布
    # print(f"\n🎓 学历要求分布:")
    edu_levels = {}
    for j in jobs:
        edu = j.get("学历要求", "不限")
        if not edu:
            edu = "不限"
        edu_levels[edu] = edu_levels.get(edu, 0) + 1
    # for edu, count in sorted(edu_levels.items(), key=lambda x: x[1], reverse=True):
    #     print(f"  - {edu}: {count} 个 ({count/len(jobs)*100:.1f}%)")

    # 4. 经验要求分布
    # print(f"\n💼 经验要求分布:")
    exp_levels = {}
    for j in jobs:
        exp = j.get("经验要求", "不限")
        if not exp:
            exp = "不限"
        exp_levels[exp] = exp_levels.get(exp, 0) + 1
    # for exp, count in sorted(exp_levels.items(), key=lambda x: x[1], reverse=True):
    #     print(f"  - {exp}: {count} 个 ({count/len(jobs)*100:.1f}%)")

    # 5. 公司规模分布
    # print(f"\n🏢 公司规模分布:")
    size_levels = {}
    for j in jobs:
        size = j.get("公司规模", "未知")
        if not size:
            size = "未知"
        size_levels[size] = size_levels.get(size, 0) + 1
    # for size, count in sorted(size_levels.items(), key=lambda x: x[1], reverse=True)[:5]:
    #     print(f"  - {size}: {count} 个")

    # 6. 热门技能标签 Top 10
    # print(f"\n🏷️ 热门技能标签 Top 10:")
    skill_count = {}
    for j in jobs:
        skills = j.get("技能标签", "")
        if skills:
            for skill in skills.split(", "):
                if skill.strip():
                    skill_count[skill] = skill_count.get(skill, 0) + 1
    # for skill, count in sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:10]:
    #     print(f"  - {skill}: {count} 次")

    # 7. 薪资最高的前10个岗位
    # print(f"\n🏆 薪资最高的 Top 10 岗位:")
    sorted_jobs = sorted(
        [j for j in jobs if j.get("薪资") and "面议" not in j.get("薪资") and "天" not in j.get("薪资")],
        key=lambda x: extract_salary_value(x.get("薪资", "0")),
        reverse=True
    )[:10]
    for i, j in enumerate(sorted_jobs, 1):
        salary = j.get("薪资", "")
        if salary:
            print(f"  {i:2d}. {j.get('职位名称', '')[:20]} | {salary} | {j.get('公司名称', '')[:15]}")

    print(f"\n{'='*70}")
    print(f"✅ 爬取完成！")
    # print(f"📁 数据已保存到: {output_path}")
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return {
        "jobs": jobs,
        "stats": {
            "total_jobs": len(jobs),
            "total_companies": len(companies),
            "avg_salary": avg_salary if salary_list else None,
            "max_salary": max(salary_list) if salary_list else None,
            "salary_distribution": salary_levels,
            "education_distribution": edu_levels,
            "experience_distribution": exp_levels,
            "top_skills": dict(sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:10]),
        }
    }


def extract_salary_value(salary_str: str) -> float:
    """从薪资字符串中提取数值（用于排序）"""
    try:
        nums = re.findall(r"[\d.]+", salary_str.replace("万", "0000").replace("千", "000"))
        if nums:
            value = float(nums[-1])
            if "万" in salary_str:
                value *= 10000
            elif "千" in salary_str:
                value *= 1000
            return value
    except:
        pass
    return 0


# ========== 岗位爬取缓存与后台入库 ==========
# 相同城市+关键词组合在有效期内不重复爬取
_JOB_CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "rag_knowladge" / "job_cache.json"
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


def _bg_scrape_and_store(city: str, keywords: list, ck: str):
    """后台线程：爬取智联 JD + LLM 摘要 + 写入向量库（带时间预算兜底）

    RAG 组件在函数内延迟导入，避免仅需要爬取能力的调用方引入向量库依赖。
    """
    global _job_bg_thread
    try:
        result = get_job_summary(city, keywords, output_filename=None, time_budget=_JOB_SCRAPE_TIME_BUDGET)
        jobs = result.get("jobs", [])
        if not jobs:
            print("[后台] 爬虫未获取到 JD 数据")
            return
        from rag.ModelServer import SummServer
        from rag.ChromaServer import ChromaServer

        content = SummServer(jobs, "CHROMA_PROMPT").content
        list_summ = [s for s in content.split('\n') if s.strip() and s.strip() != "none"]
        if list_summ:
            chroma = ChromaServer()
            chroma.batch_storage(list_summ)
        # 更新缓存
        cache = _load_job_cache()
        cache[ck] = int(time.time())
        _save_job_cache(cache)
        print(f"[后台] JD 爬取+向量化完成，{len(list_summ)} 条摘要已入库")
    except Exception as e:
        print(f"[后台] JD 爬取失败: {e}")
    finally:
        with _job_bg_lock:
            _job_bg_thread = None


def ensure_bg_scrape(city: str, keywords: list) -> bool:
    """需要时在后台线程爬取 JD 并向量化入库（缓存有效期内不重复爬取）。

    Returns:
        True=已启动后台任务或任务已在运行；False=无有效入参
    """
    global _job_bg_thread
    if not city or not keywords:
        return False
    ck = _cache_key(city, keywords)
    cache = _load_job_cache()
    cached_time = cache.get(ck, 0)
    if (int(time.time()) - cached_time) < _JOB_CACHE_TTL:
        return True  # 缓存有效，无需重复爬取
    with _job_bg_lock:
        if _job_bg_thread is not None and _job_bg_thread.is_alive():
            return True  # 已有相同任务在跑
        _job_bg_thread = threading.Thread(
            target=_bg_scrape_and_store,
            args=(city, keywords, ck),
            daemon=True,
        )
        _job_bg_thread.start()
    return True


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 示例1：爬取成都的 AI Agent 相关岗位
    result = get_job_summary(
        city_name="成都",
        keywords=[
            "AI智能体",
            "AI Agent",
            "大模型 agent",
            "智能体开发",
            "AI应用开发"
        ]
    )
    

    print(f"##########################{result}")
    # 示例2：爬取上海的前端岗位
    # result = get_job_summary(
    #     city_name="上海",
    #     keywords=["前端开发", "React", "Vue"],
    #     output_filename="上海前端岗位.csv"
    # )
    
    # 示例3：只获取数据，不保存（可以自行处理）
    # result = get_job_summary(
    #     city_name="北京",
    #     keywords=["Python开发"],
    #     output_filename=None  # 自动生成文件名
    # )
    # 访问数据
    # for job in result['jobs']:
    #     print(job['职位名称'], job['薪资'])