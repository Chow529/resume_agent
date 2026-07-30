#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话模型类 - 处理会话记录管理

会话表结构设计：
- chat_sessions: 存储会话元数据（1个用户多个会话）
- chat_session_contents: 存储会话内容（1个会话多条内容记录）
"""

from typing import Optional, Dict, Any, List
from mysql_connector import BaseModel, MySQLConnector


class ChatSessionModel(BaseModel):
    """会话模型类，处理会话元数据管理"""

    def __init__(self, db: Optional[MySQLConnector] = None):
        super().__init__('chat_sessions', db)

    def create_session(self, user_id: int, session_name: str) -> Optional[int]:
        """创建新会话"""
        data = {
            'user_id': user_id,
            'session_name': session_name
        }
        return self.create(data)

    def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        """通过会话 ID 获取会话"""
        return self.get(session_id)

    def get_sessions_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """获取指定用户的所有会话"""
        return self.get_all_by('user_id', user_id)

    def delete_session(self, session_id: int) -> int:
        """删除会话（外键 ON DELETE CASCADE 会自动删除关联的内容记录）"""
        return self.delete(session_id)

    def update_session(self, session_id: int, name: str) -> int:
        """更新会话名称"""
        return self.update(session_id, {'session_name': name})


class ChatSessionContentModel(BaseModel):
    """会话内容模型类，存储会话中的每条消息记录"""

    def __init__(self, db: Optional[MySQLConnector] = None):
        super().__init__('chat_session_contents', db)

    def add_content(self, session_id: int, role: str, content: str) -> Optional[int]:
        """添加一条会话内容记录"""
        # 验证 role 的有效性
        valid_roles = ['user', 'assistant', 'system']
        if role not in valid_roles:
            raise ValueError(f"role 必须是 {valid_roles} 中的一个")

        data = {
            'session_id': session_id,
            'role': role,
            'content': content
        }
        return self.create(data)

    def get_contents_by_session(self, session_id: int) -> List[Dict[str, Any]]:
        """获取会话的所有内容记录（按时间顺序）"""
        sql = f"SELECT * FROM `{self.table_name}` WHERE session_id = %s ORDER BY created_at ASC"
        results = self.db.execute_query(sql, (session_id,))
        return results

    def get_contents_by_session_and_role(self, session_id: int, role: str) -> List[Dict[str, Any]]:
        """获取会话中特定角色的所有记录"""
        sql = f"SELECT * FROM `{self.table_name}` WHERE session_id = %s AND role = %s ORDER BY created_at ASC"
        results = self.db.execute_query(sql, (session_id, role))
        return results

    def delete_contents_by_session(self, session_id: int) -> int:
        """删除会话的所有内容记录"""
        sql = f"DELETE FROM `{self.table_name}` WHERE session_id = %s"
        return self.db.execute_update(sql, (session_id,))


# ========== 使用示例 ==========

if __name__ == '__main__':
    # 创建模型实例
    session_model = ChatSessionModel()
    content_model = ChatSessionContentModel()

    try:
        print("="*60)
        print("会话记录管理示例")
        print("="*60)

        # 1. 创建会话
        print("\n步骤 1: 创建新会话")
        session_id = session_model.create_session(user_id=1, session_name="测试会话")
        print(f"✓ 会话创建成功，ID: {session_id}")
      
        if session_id:
            # 2. 添加内容记录
            print("\n步骤 2: 添加会话内容记录")
            content_model.add_content(session_id, 'user', "你好，请介绍一下你的功能？")
            content_model.add_content(session_id, 'assistant', "我是 AI 助手，我可以帮助你解答问题、提供建议等。")
            content_model.add_content(session_id, 'user', "你能帮我写一段 Python 代码吗？")
            content_model.add_content(session_id, 'assistant', "当然可以！请告诉我你想要实现什么功能？")
            print(f"✓ 添加了 {content_model.get_contents_by_session(session_id)} 条内容记录")

            # 3. 查询所有会话内容
            print("\n步骤 3: 查询会话内容")
            contents = content_model.get_contents_by_session(session_id)
            print(f"会话内容 ({len(contents)} 条):")
            for c in contents:
                print(f"  [{c['role']}] {c['content']}")

            # 4. 按角色查询内容
            print("\n步骤 4: 按角色查询内容")
            user_contents = content_model.get_contents_by_session_and_role(session_id, 'user')
            assistant_contents = content_model.get_contents_by_session_and_role(session_id, 'assistant')
            print(f"用户消息: {len(user_contents)} 条")
            print(f"助手消息: {len(assistant_contents)} 条")

            # 5. 删除会话（会自动级联删除内容记录）
            print("\n步骤 5: 删除会话")
            deleted = session_model.delete_session(session_id)
            print(f"✓ 删除会话，影响行数: {deleted}")
            # 验证内容也被删除
            remaining = content_model.get_contents_by_session(session_id)
            print(f"剩余内容记录: {len(remaining)} 条 (应为 0)")

    except Exception as e:
        print(f"\n✗ 操作失败: {e}")
    finally:
        session_model.close()
        content_model.close()
        print("\n✓ 连接已关闭")
