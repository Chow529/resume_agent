#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JobJdModel - 岗位 JD 数据模型

管理 job_jds 表：用户通过采集模块（智联招聘等）爬取到的岗位 JD。
- 个人数据：is_public=0，仅所有者可见
- 公用数据：is_public=1，所有用户可见
"""

from typing import Optional, List, Dict, Any
from sqlClass.mysql_connector import BaseModel


# 表中除主键 / 时间戳外的业务字段（供批量写入使用）
_JD_FIELDS = [
    'user_id', 'source', 'source_job_id', 'job_name', 'company_name',
    'salary', 'city', 'district', 'education', 'experience',
    'company_size', 'industry', 'financing_stage', 'skill_tags',
    'welfare', 'labels', 'keyword', 'job_url', 'jd_content',
    'raw_json', 'is_public',
]


class JobJdModel(BaseModel):
    """岗位 JD 模型类，继承自 BaseModel，操作 job_jds 表"""

    def __init__(self):
        super().__init__('job_jds')

    def upsert_one(self, row: Dict[str, Any]) -> str:
        """插入或更新一条 JD（按 user_id+source+source_job_id 去重）

        Returns:
            'inserted' 新插入 | 'updated' 已存在被更新
        """
        data = {k: row.get(k) for k in _JD_FIELDS}
        data.setdefault('is_public', 0)
        cols = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        # 重复爬取时更新 JD 内容，但保留用户设置的 is_public 不变
        update_cols = [k for k in data.keys() if k not in ('user_id', 'is_public')]
        update_clause = ', '.join([f"{k} = VALUES({k})" for k in update_cols])
        sql = (
            f"INSERT INTO `{self.table_name}` ({cols}) VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {update_clause}"
        )
        rowcount = self.db.execute_update(sql, tuple(data.values()))
        # MySQL: 插入=1，更新=2
        return 'updated' if rowcount >= 2 else 'inserted'

    def upsert_many(self, rows: List[Dict[str, Any]]) -> Dict[str, int]:
        """批量 upsert，返回 {'inserted': n, 'updated': n, 'total': n}"""
        result = {'inserted': 0, 'updated': 0, 'total': len(rows)}
        for row in rows:
            action = self.upsert_one(row)
            result[action] += 1
        return result

    def get_by_id(self, jd_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取单条 JD"""
        return self.get(jd_id)

    def list_personal(self, user_id: int, keyword: str = None) -> List[Dict[str, Any]]:
        """获取用户个人 JD（仅未公开的私有数据，已公开的进入公用数据列表）"""
        sql = f"SELECT * FROM `{self.table_name}` WHERE user_id = %s AND is_public = 0"
        params: list = [user_id]
        if keyword:
            sql += " AND (job_name LIKE %s OR company_name LIKE %s OR keyword LIKE %s)"
            like = f"%{keyword}%"
            params.extend([like, like, like])
        sql += " ORDER BY created_at DESC"
        return self.db.execute_query(sql, tuple(params))

    def list_public(self, keyword: str = None) -> List[Dict[str, Any]]:
        """获取公用 JD（所有用户公开的数据）"""
        sql = f"SELECT * FROM `{self.table_name}` WHERE is_public = 1"
        params: list = []
        if keyword:
            sql += " AND (job_name LIKE %s OR company_name LIKE %s OR keyword LIKE %s)"
            like = f"%{keyword}%"
            params.extend([like, like, like])
        sql += " ORDER BY created_at DESC"
        return self.db.execute_query(sql, tuple(params))

    def search_choices(self, user_id: int, keywords: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        """按岗位关键词检索可选 JD（本人数据 + 公用数据），供未选岗时的 AI 推荐使用

        匹配 job_name / company_name / keyword 字段，本人数据优先、使用次数高者优先。
        """
        kws = [k.strip() for k in (keywords or []) if k and k.strip()]
        if not kws:
            return []
        conds, params = [], [user_id]
        for kw in kws:
            like = f"%{kw}%"
            conds.append("(job_name LIKE %s OR company_name LIKE %s OR keyword LIKE %s)")
            params.extend([like, like, like])
        sql = (
            f"SELECT * FROM `{self.table_name}` "
            f"WHERE (user_id = %s OR is_public = 1) AND ({' OR '.join(conds)}) "
            f"ORDER BY (user_id = %s) DESC, use_count DESC, created_at DESC LIMIT %s"
        )
        params.extend([user_id, int(limit)])
        return self.db.execute_query(sql, tuple(params))

    def list_choices(self, user_id: int) -> List[Dict[str, Any]]:
        """获取面试可选 JD：本人数据 + 公用数据，按岗位去重（优先保留本人数据）"""
        sql = (
            f"SELECT * FROM `{self.table_name}` "
            f"WHERE user_id = %s OR is_public = 1 "
            f"ORDER BY (user_id = %s) DESC, created_at DESC"
        )
        rows = self.db.execute_query(sql, (user_id, user_id))
        # 同一来源岗位去重（本人数据因排序优先会被保留）
        seen = set()
        deduped = []
        for r in rows:
            key = (r.get('source'), r.get('source_job_id'))
            if key in seen:
                continue
            seen.add(key)
            r['scope'] = 'personal' if r.get('user_id') == user_id else 'public'
            deduped.append(r)
        return deduped

    def set_public(self, jd_id: int, user_id: int, is_public: int) -> int:
        """设置公开状态（仅数据所有者可操作，且只允许 私有→公用，公用不可改回私有）"""
        if not is_public:
            raise ValueError("公用数据不允许改回个人数据")
        sql = (
            f"UPDATE `{self.table_name}` SET is_public = %s "
            f"WHERE id = %s AND user_id = %s AND is_public = 0"
        )
        return self.db.execute_update(sql, (1, jd_id, user_id))

    def increment_use_count(self, jd_id: int) -> int:
        """使用次数 +1（用户开始面试并选择该岗位时调用）"""
        sql = f"UPDATE `{self.table_name}` SET use_count = use_count + 1 WHERE id = %s"
        return self.db.execute_update(sql, (jd_id,))

    def list_personal_ranking(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """个人排名：本人 JD 按使用次数降序（用的多的靠前）"""
        sql = (
            f"SELECT id, job_name, company_name, salary, city, district, keyword, source, "
            f"use_count, is_public, created_at "
            f"FROM `{self.table_name}` WHERE user_id = %s "
            f"ORDER BY use_count DESC, created_at DESC LIMIT %s"
        )
        return self.db.execute_query(sql, (user_id, int(limit)))

    def list_public_ranking(self, limit: int = 50) -> List[Dict[str, Any]]:
        """公用排名：所有用户的使用次数汇总（同一岗位被多个用户公开时按岗位合并累计）"""
        sql = (
            f"SELECT MAX(id) AS id, source, source_job_id, "
            f"MAX(job_name) AS job_name, MAX(company_name) AS company_name, "
            f"MAX(salary) AS salary, MAX(city) AS city, MAX(keyword) AS keyword, "
            f"SUM(use_count) AS use_count "
            f"FROM `{self.table_name}` WHERE is_public = 1 "
            f"GROUP BY source, source_job_id "
            f"ORDER BY use_count DESC LIMIT %s"
        )
        return self.db.execute_query(sql, (int(limit),))

    def delete_for_user(self, jd_id: int, user_id: int) -> int:
        """删除 JD（仅数据所有者可操作）"""
        sql = f"DELETE FROM `{self.table_name}` WHERE id = %s AND user_id = %s"
        return self.db.execute_update(sql, (jd_id, user_id))

    def is_owner_or_public(self, jd_id: int, user_id: int) -> bool:
        """判断用户是否有权使用该 JD（本人数据或公用数据）"""
        row = self.get_by_id(jd_id)
        if not row:
            return False
        return row.get('user_id') == user_id or row.get('is_public') == 1
