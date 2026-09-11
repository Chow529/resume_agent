#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据采集模块包

导入本包即自动注册所有采集器。新增采集模块时，
在此处 import 一次对应模块即可在注册表中生效。
"""
from . import zhaopin_collector  # noqa: F401  导入即注册智联招聘采集器
from .registry import (
    get_collector,
    list_collectors,
    list_modules_metadata,
    register_collector,
)

__all__ = [
    "get_collector",
    "list_collectors",
    "list_modules_metadata",
    "register_collector",
]
