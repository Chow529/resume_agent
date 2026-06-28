"""
智联招聘爬虫 - 支持自定义地区和关键词
使用 curl_cffi 模拟 Chrome TLS 指纹绕过反爬
输出 CSV 文件
"""
import csv
import json
import re
import time
import os
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
            timeout=20,
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
        "职位URL": position_url,
        "公司URL": pos.get("companyUrl", ""),
        "搜索关键词": "",  # 后续填充
    }


def scrape_all(city_name: str, keywords: list) -> list:
    """
    主爬取逻辑
    
    Args:
        city_name: 城市名称，如 "成都"
        keywords: 搜索关键词列表，如 ["AI智能体", "AI Agent"]
    
    Returns:
        list: 职位数据列表
    """
    # 获取城市代码
    city_code = CITY_CODE_MAP.get(city_name)
    if not city_code:
        print(f"❌ 错误：不支持的城市 '{city_name}'")
        print(f"   支持的城市列表: {', '.join(CITY_CODE_MAP.keys())}")
        return []
    
    all_jobs = {}  # 用 jobId 去重
    total_pages = 0
    total_positions = 0

    for keyword in keywords:
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
        print(f"  📊 共找到 {position_count} 个职位，{pages} 页")

        # 处理第一页
        for pos in state.get("positionList", []):
            job_id = pos.get("jobId") or pos.get("number") or pos.get("uuid")
            if job_id and job_id not in all_jobs:
                parsed = parse_job(pos)
                parsed["搜索关键词"] = keyword
                all_jobs[job_id] = parsed

        total_pages += pages
        total_positions += position_count

        # 获取后续页面
        for page in range(2, pages + 1):
            print(f"  🔄 正在获取第 {page}/{pages} 页...")
            time.sleep(REQUEST_DELAY)
            state = search_jobs(keyword, city_code, page=page)
            if not state:
                print(f"  ⚠️ 第 {page} 页获取失败，跳过")
                continue
            for pos in state.get("positionList", []):
                job_id = pos.get("jobId") or pos.get("number") or pos.get("uuid")
                if job_id and job_id not in all_jobs:
                    parsed = parse_job(pos)
                    parsed["搜索关键词"] = keyword
                    all_jobs[job_id] = parsed

        time.sleep(REQUEST_DELAY)

    print(f"\n✅ 爬取完成！共获取 {len(all_jobs)} 条去重职位数据")
    return list(all_jobs.values())


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

    print(f"💾 CSV 已保存到: {filename}")
    print(f"📊 共 {len(jobs)} 条职位数据")


def get_job_summary(city_name: str, keywords: list, output_filename: str = None):
    """
    灵活的任务总结函数
    
    Args:
        city_name: 城市名称（中文），如 "成都"
        keywords: 搜索关键词列表，如 ["AI智能体", "AI Agent", "大模型 agent"]
        output_filename: 输出文件名（可选），如不指定则自动生成
    
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
    print(f"📁 输出文件: {output_filename}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 爬取数据
    jobs = scrape_all(city_name, keywords)

    if not jobs:
        print("❌ 未获取到任何职位数据！")
        return {"jobs": [], "stats": {}}

    # 保存 CSV
    output_path = os.path.join(os.path.dirname(__file__), output_filename)
    save_csv(jobs, output_path)

    # ========== 统计分析 ==========
    print(f"\n{'='*70}")
    print("📈 统计分析")
    print("=" * 70)

    # 1. 总体统计
    companies = set(j.get("公司名称", "") for j in jobs if j.get("公司名称"))
    print(f"\n📊 总体统计:")
    print(f"  - 去重后职位数: {len(jobs)}")
    print(f"  - 涉及公司数: {len(companies)}")

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

    print(f"\n💰 薪资分布:")
    for level, count in salary_levels.items():
        if count > 0:
            print(f"  - {level}: {count} 个 ({count/len(jobs)*100:.1f}%)")

    # 计算平均薪资（仅统计有明确薪资的）
    if salary_list:
        avg_salary = sum(salary_list) / len(salary_list)
        print(f"\n  📊 平均薪资（有明确薪资的岗位）: {avg_salary/10000:.1f}K/月")
        print(f"  💰 最高薪资: {max(salary_list)/10000:.1f}K/月")
        print(f"  💰 最低薪资: {min(salary_list)/10000:.1f}K/月")

    # 3. 学历要求分布
    print(f"\n🎓 学历要求分布:")
    edu_levels = {}
    for j in jobs:
        edu = j.get("学历要求", "不限")
        if not edu:
            edu = "不限"
        edu_levels[edu] = edu_levels.get(edu, 0) + 1
    for edu, count in sorted(edu_levels.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {edu}: {count} 个 ({count/len(jobs)*100:.1f}%)")

    # 4. 经验要求分布
    print(f"\n💼 经验要求分布:")
    exp_levels = {}
    for j in jobs:
        exp = j.get("经验要求", "不限")
        if not exp:
            exp = "不限"
        exp_levels[exp] = exp_levels.get(exp, 0) + 1
    for exp, count in sorted(exp_levels.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {exp}: {count} 个 ({count/len(jobs)*100:.1f}%)")

    # 5. 公司规模分布
    print(f"\n🏢 公司规模分布:")
    size_levels = {}
    for j in jobs:
        size = j.get("公司规模", "未知")
        if not size:
            size = "未知"
        size_levels[size] = size_levels.get(size, 0) + 1
    for size, count in sorted(size_levels.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  - {size}: {count} 个")

    # 6. 热门技能标签 Top 10
    print(f"\n🏷️ 热门技能标签 Top 10:")
    skill_count = {}
    for j in jobs:
        skills = j.get("技能标签", "")
        if skills:
            for skill in skills.split(", "):
                if skill.strip():
                    skill_count[skill] = skill_count.get(skill, 0) + 1
    for skill, count in sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {skill}: {count} 次")

    # 7. 薪资最高的前10个岗位
    print(f"\n🏆 薪资最高的 Top 10 岗位:")
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
    print(f"📁 数据已保存到: {output_path}")
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