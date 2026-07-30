#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ResumeModel - 简历数据模型
管理 user_resumes 表，支持简历上传、激活、删除等完整生命周期管理

对应 SQL 表结构:
  id, user_id, filename, file_path (TEXT, 存储 markitdown 提取的文本),
  uploaded_at (CURRENT_TIMESTAMP), is_active (default 1)
"""

from typing import Optional, List, Dict, Any
from sqlClass.mysql_connector import BaseModel


class ResumeModel(BaseModel):
    """简历模型类，继承自 BaseModel，操作 user_resumes 表"""

    def __init__(self):
        super().__init__('user_resumes')

    def create(self, user_id: int, filename: str, resume_text: str) -> Optional[int]:
        """
        创建新的简历记录
        检查该用户是否已上传了3份简历（上限）
        resume_text 存储 markitdown 提取的纯文本内容

        Args:
            user_id: 用户 ID
            filename: 原始文件名
            resume_text: markitdown 提取的简历文本内容
        """
        if self.get_active_count(user_id) >= 3:
            return None

        data = {
            'user_id': user_id,
            'filename': filename,
            'file_path': resume_text,  # 存储纯文本，不存文件路径
            'is_active': 1
        }
        return super().create(data)

    def get_active_count(self, user_id: int) -> int:
        """获取用户当前激活的简历数量"""
        sql = f"SELECT COUNT(*) AS count FROM `{self.table_name}` WHERE user_id = %s AND is_active = 1"
        result = self.db.execute_query(sql, (user_id,))
        return result[0]['count'] if result else 0

    def get_all(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户所有记录（按上传时间倒序）"""
        sql = f"SELECT * FROM `{self.table_name}` WHERE user_id = %s ORDER BY uploaded_at DESC"
        return self.db.execute_query(sql, (user_id,))

    def get_active(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户当前激活的简历"""
        results = self.db.execute_query(
            f"SELECT * FROM `{self.table_name}` WHERE user_id = %s AND is_active = 1 ORDER BY uploaded_at DESC LIMIT 1",
            (user_id,)
        )
        return results[0] if results else None

    def set_active(self, user_id: int, resume_id: int) -> bool:
        """激活指定简历（同时取消该用户其他激活状态）"""
        self.update_all(user_id, {'is_active': 0})
        return self.update(resume_id, {'is_active': 1}) > 0

    def update_all(self, user_id: int, data: Dict[str, Any]) -> int:
        """更新用户所有记录"""
        set_clause = ', '.join([f'{k} = %s' for k in data.keys()])
        values = tuple(data.values()) + (user_id,)
        sql = f"UPDATE `{self.table_name}` SET {set_clause} WHERE user_id = %s"
        return self.db.execute_update(sql, values)

    def deactivate(self, resume_id: int) -> int:
        """逻辑删除（设为不激活）"""
        return self.update(resume_id, {'is_active': 0})

    def get_by_id(self, resume_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取单条记录"""
        return self.get(resume_id)
