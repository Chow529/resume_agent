#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据采集模块基类

后续新增采集来源（如其他招聘网站、面经网站等）时：
1. 新建一个 collector 文件，继承 BaseCollector 并实现 scrape()；
2. 用 @register_collector 注册到 registry；
3. 前端数据中心会自动通过 /api/data-center/modules 拿到新模块元数据。

如果新模块采集的仍是"岗位JD"类数据，直接映射为 job_jds 行即可；
若是全新数据类型，再新建对应表与 Model 类（一表一类）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class CollectorParam:
    """采集参数定义（用于前端自动渲染参数表单）"""
    name: str                         # 参数名，scrape(params) 取值用
    label: str                        # 界面显示名
    type: str = "text"                # text / textarea / number / select
    required: bool = False
    default: Any = None
    placeholder: str = ""
    options: List[Dict[str, str]] = field(default_factory=list)  # type=select 时：[{label, value}]


@dataclass
class ScrapeResult:
    """采集结果：映射后的 job_jds 行（不含 user_id / is_public，由上层补）"""
    rows: List[Dict[str, Any]]
    stats: Dict[str, Any] = field(default_factory=dict)


# 进度回调签名：(当前关键词/阶段, 当前页, 已采集条数, 总页数)
ProgressCallback = Callable[[str, int, int, int], None]


class BaseCollector(ABC):
    """采集器基类"""

    key: str = ""           # 唯一标识，写入 job_jds.source
    name: str = ""          # 界面显示名称
    description: str = ""   # 模块说明
    params: List[CollectorParam] = []

    @abstractmethod
    def scrape(self, params: Dict[str, Any], on_progress: Optional[ProgressCallback] = None) -> ScrapeResult:
        """执行采集，返回映射为 job_jds 行的结果"""
        raise NotImplementedError

    def metadata(self) -> Dict[str, Any]:
        """返回给前端的模块元数据"""
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "params": [
                {
                    "name": p.name,
                    "label": p.label,
                    "type": p.type,
                    "required": p.required,
                    "default": p.default,
                    "placeholder": p.placeholder,
                    "options": p.options,
                }
                for p in self.params
            ],
        }
