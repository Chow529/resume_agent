#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理工具 - 简历文件的上传和删除
"""

import os
from pathlib import Path


def save_resume_file(user_id: int, filename: str, raw_bytes: bytes) -> str:
    """
    将原始文件保存到指定目录（覆盖已存在的文件）

    Args:
        user_id: 用户ID
        filename: 文件名（不含路径）
        raw_bytes: 文件二进制内容

    Returns:
        文件的完整路径（字符串）
    """
    # 项目根目录下的 uploads/user_id/ 文件夹
    project_root = Path(__file__).parent.parent.parent  # 从 backend/utils/ 回到项目根
    upload_dir = project_root / "uploads" / str(user_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / filename

    # 直接覆盖已存在的文件
    with open(file_path, "wb") as f:
        f.write(raw_bytes)

    return str(file_path)


def delete_resume_file(file_path: str) -> bool:
    """
    删除原始简历文件

    Args:
        file_path: 文件的完整路径

    Returns:
        是否删除成功（True/False）
    """
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            return True
        return False  # 文件不存在
    except Exception:
        return False  # 删除失败