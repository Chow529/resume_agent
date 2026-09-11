#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智联招聘岗位 JD 采集器

复用 collectors/tools/zhaopin_scraper.py 中的爬取接口（get_job_summary），
把爬取结果映射为 job_jds 表行。
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .base import BaseCollector, CollectorParam, ProgressCallback, ScrapeResult
from .registry import register_collector

# 复用保留的爬取接口
from .tools.zhaopin_scraper import CITY_CODE_MAP, get_job_summary


# 爬虫原始字段（中文） -> job_jds 表字段
_FIELD_MAP = {
    "职位ID": "source_job_id",
    "职位名称": "job_name",
    "公司名称": "company_name",
    "薪资": "salary",
    "城市": "city",
    "区域": "district",
    "学历要求": "education",
    "经验要求": "experience",
    "公司规模": "company_size",
    "公司行业": "industry",
    "融资阶段": "financing_stage",
    "技能标签": "skill_tags",
    "福利": "welfare",
    "标签": "labels",
    "搜索关键词": "keyword",
    "职位URL": "job_url",
}

# 拼装 jd_content 文本时的展示字段（顺序即展示顺序）
_CONTENT_FIELDS = [
    ("职位名称", "岗位名称"),
    ("公司名称", "公司名称"),
    ("薪资", "薪资"),
    ("城市", "工作城市"),
    ("区域", "工作区域"),
    ("学历要求", "学历要求"),
    ("经验要求", "经验要求"),
    ("公司规模", "公司规模"),
    ("公司行业", "公司行业"),
    ("融资阶段", "融资阶段"),
    # 完整 JD（岗位职责/任职要求），来自岗位详情页；缺失时由爬虫用列表预览/结构化字段兜底
    ("职位描述", "岗位职责与任职要求"),
    ("技能标签", "技能要求"),
    ("福利", "福利待遇"),
    ("标签", "岗位标签"),
    ("招聘人数", "招聘人数"),
    ("职位类型", "职位类型"),
    ("发布日期", "发布日期"),
    ("职位URL", "岗位链接"),
]


def _build_jd_content(job: Dict[str, Any]) -> str:
    """把岗位字段拼装为供面试提问使用的 JD 文本"""
    lines = []
    for raw_key, label in _CONTENT_FIELDS:
        value = job.get(raw_key)
        if value not in (None, "", []):
            lines.append(f"{label}：{value}")
    return "\n".join(lines)


@register_collector
class ZhaopinCollector(BaseCollector):
    """智联招聘采集器"""

    key = "zhaopin"
    name = "智联招聘"
    description = "按城市与岗位关键词爬取智联招聘在招岗位 JD，存入你的个人数据库"

    params = [
        CollectorParam(
            name="city", label="工作城市", type="select", required=True,
            options=[{"label": city, "value": city} for city in CITY_CODE_MAP.keys()],
        ),
        CollectorParam(
            name="keywords", label="岗位关键词", type="textarea", required=True,
            placeholder="多个关键词用英文逗号分隔，如：AI Agent,大模型应用开发,RAG",
        ),
        CollectorParam(
            name="time_budget", label="爬取时间预算（秒）", type="number",
            required=False, default=90, placeholder="超时后返回已采集数据，默认90秒",
        ),
    ]

    def scrape(self, params: Dict[str, Any], on_progress: Optional[ProgressCallback] = None) -> ScrapeResult:
        city = (params.get("city") or "").strip()
        raw_keywords = params.get("keywords") or ""
        if isinstance(raw_keywords, list):
            keywords = [str(k).strip() for k in raw_keywords if str(k).strip()]
        else:
            keywords = [k.strip() for k in str(raw_keywords).replace("，", ",").split(",") if k.strip()]
        try:
            time_budget = int(params.get("time_budget") or 90)
        except (TypeError, ValueError):
            time_budget = 90

        if not city:
            raise ValueError("请选择工作城市")
        if city not in CITY_CODE_MAP:
            raise ValueError(f"暂不支持城市：{city}")
        if not keywords:
            raise ValueError("请至少填写一个岗位关键词")

        result = get_job_summary(
            city_name=city,
            keywords=keywords,
            output_filename=None,
            time_budget=time_budget,
            on_progress=on_progress,
        )
        jobs = result.get("jobs", []) if isinstance(result, dict) else []

        rows = []
        for job in jobs:
            row: Dict[str, Any] = {"source": self.key}
            for raw_key, col in _FIELD_MAP.items():
                row[col] = job.get(raw_key)
            # 兜底：没有岗位ID时用岗位URL，保证去重键非空
            if not row.get("source_job_id"):
                row["source_job_id"] = row.get("job_url") or f"{row.get('job_name','')}_{row.get('company_name','')}"
            row["jd_content"] = _build_jd_content(job)
            row["raw_json"] = json.dumps(job, ensure_ascii=False)
            rows.append(row)

        return ScrapeResult(rows=rows, stats=result.get("stats", {}) if isinstance(result, dict) else {})
