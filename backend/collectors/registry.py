#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
采集器注册表

新增采集模块只需：
    from collectors.registry import register_collector

    @register_collector
    class MyCollector(BaseCollector):
        key = "xxx"
        ...
并在 collectors/__init__.py 中 import 一次即可自动注册。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Type

from .base import BaseCollector

# key -> 采集器实例
_REGISTRY: Dict[str, BaseCollector] = {}


def register_collector(cls: Type[BaseCollector]) -> Type[BaseCollector]:
    """类装饰器：注册一个采集器"""
    instance = cls()
    if not instance.key:
        raise ValueError(f"采集器 {cls.__name__} 必须定义 key")
    _REGISTRY[instance.key] = instance
    return cls


def get_collector(key: str) -> Optional[BaseCollector]:
    return _REGISTRY.get(key)


def list_collectors() -> List[BaseCollector]:
    return list(_REGISTRY.values())


def list_modules_metadata() -> List[dict]:
    """返回所有采集模块的元数据（供 /api/data-center/modules）"""
    return [c.metadata() for c in _REGISTRY.values()]
