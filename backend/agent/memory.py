"""
Agent 记忆管理

把原先散落在 web_app 中的记忆相关逻辑收敛到一个记忆类中：

- 短记忆（上下文）：内存中的会话上下文消息，拼接进 prompt 传给大模型
- 长记忆（持久化）：写入数据库的会话与消息，可跨请求 / 跨会话恢复

用法::

    from agent.memory import memory

    memory.init_session(session_id)
    memory.add_user_message(session_id, "你好")
    messages = memory.build_prompt_messages(session_id)
    memory.save_message(session_id, "assistant", "你好，我是面试官")
"""

from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# 确保可以导入 backend 下的顶层包（utils / sqlClass）
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from utils.logging_tool import logger

# 短记忆保留的最大历史消息条数，避免超出 token 限制
DEFAULT_MAX_HISTORY = 20


class AgentMemory:
    """Agent 记忆类：统一管理短记忆（上下文）与长记忆（数据库）"""

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY):
        self.max_history = max_history
        # 短记忆存储：session_id -> 会话上下文
        self._sessions: Dict[str, Dict[str, Any]] = {}

    # ============================================================
    # 短记忆（上下文，拼入 prompt）
    # ============================================================
    def init_session(self, session_id: str) -> Dict[str, Any]:
        """初始化一个会话（仅内存，不创建数据库记录）"""
        session_data = {
            "chat_history": [],
            "status": "initialized",
            "created_at": int(time.time()),
            "db_session_id": None,
            "question_count": 0,
        }
        self._sessions[session_id] = session_data
        return session_data

    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    def ensure_session(self, session_id: str) -> Dict[str, Any]:
        """获取会话，不存在则初始化"""
        if session_id not in self._sessions:
            self.init_session(session_id)
        return self._sessions[session_id]

    # ---- 上下文消息 ----
    def get_history(self, session_id: str) -> List[BaseMessage]:
        """获取当前会话的上下文消息（短记忆）"""
        return self.ensure_session(session_id)["chat_history"]

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        self.ensure_session(session_id)["chat_history"].append(message)

    def add_user_message(self, session_id: str, content: str) -> None:
        self.add_message(session_id, HumanMessage(content=content))

    def add_ai_message(self, session_id: str, content: str) -> None:
        self.add_message(session_id, AIMessage(content=content))

    def clear_history(self, session_id: str) -> None:
        """清空上下文并重置轮次计数"""
        session = self.ensure_session(session_id)
        session["chat_history"] = []
        session["question_count"] = 0

    def trim_history(self, session_id: str) -> List[BaseMessage]:
        """限制上下文长度，避免超出 token 限制"""
        session = self.ensure_session(session_id)
        history = session["chat_history"]
        if len(history) > self.max_history:
            history = history[-self.max_history:]
            session["chat_history"] = history
        return history

    @staticmethod
    def last_ai_message(messages: List[BaseMessage]) -> Optional[AIMessage]:
        """从消息列表中获取最后一条 AI 回复消息"""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return msg
        return None

    def build_prompt_messages(
        self,
        session_id: str,
        extra_messages: Optional[List[BaseMessage]] = None,
        inject_user_context: bool = True,
        system_prefix: Optional[str] = None,
    ) -> List[BaseMessage]:
        """构建传给大模型的上下文消息（短记忆）

        Args:
            session_id: 会话 ID
            extra_messages: 本次调用额外追加的消息（不写入历史）
            inject_user_context: 是否注入当前 user_id 的系统提示，
                避免 Agent 中途调用需要 user_id 的工具时因缺参反复重试
            system_prefix: 追加在消息最前方的系统提示（如对话边界约束）
        """
        messages: List[BaseMessage] = []
        if system_prefix:
            messages.append(SystemMessage(content=system_prefix))
        user_id = self.get_user_id(session_id)
        if inject_user_context and user_id:
            messages.append(SystemMessage(
                content=f"当前用户的 user_id 是 {user_id},调用需要 user_id 的工具时请使用该值。"
            ))
        messages.extend(self.get_history(session_id))
        if extra_messages:
            messages.extend(extra_messages)
        return messages

    # ---- 会话状态字段 ----
    def get_user_id(self, session_id: str) -> Optional[int]:
        return self.ensure_session(session_id).get("user_id")

    def set_user_id(self, session_id: str, user_id: int) -> None:
        self.ensure_session(session_id)["user_id"] = int(user_id)

    def get_db_session_id(self, session_id: str) -> Optional[int]:
        return self.ensure_session(session_id).get("db_session_id")

    def set_db_session_id(self, session_id: str, db_session_id: Optional[int]) -> None:
        self.ensure_session(session_id)["db_session_id"] = db_session_id

    def get_status(self, session_id: str) -> str:
        return self.ensure_session(session_id).get("status", "initialized")

    def set_status(self, session_id: str, status: str) -> None:
        self.ensure_session(session_id)["status"] = status

    def get_resume_text(self, session_id: str) -> Optional[str]:
        return self.ensure_session(session_id).get("resume_text")

    def set_resume_text(self, session_id: str, resume_text: str) -> None:
        self.ensure_session(session_id)["resume_text"] = resume_text

    def get_question_count(self, session_id: str) -> int:
        return self.ensure_session(session_id).get("question_count", 0)

    def increment_question_count(self, session_id: str) -> int:
        session = self.ensure_session(session_id)
        session["question_count"] = session.get("question_count", 0) + 1
        return session["question_count"]

    # ============================================================
    # 长记忆（数据库持久化）
    # ============================================================
    def save_message(self, session_id: str, role: str, content: str) -> None:
        """保存单条消息到数据库

        Args:
            role: "user" 或 "assistant"
        """
        try:
            db_session_id = self.get_db_session_id(session_id)
            if not db_session_id:
                logger.warning(f"保存消息失败: 会话 {session_id} 没有 db_session_id")
                return
            from sqlClass.chat_session_model import ChatSessionContentModel
            ChatSessionContentModel().add_content(
                session_id=db_session_id,
                role=role,
                content=content,
            )
            logger.debug(f"消息已保存: session={db_session_id}, role={role}")
        except Exception as e:
            logger.error(f"保存消息到数据库失败: {e}", exc_info=True)

    def load_history(self, db_session_id: int) -> List[BaseMessage]:
        """从数据库加载历史消息"""
        history: List[BaseMessage] = []
        try:
            from sqlClass.chat_session_model import ChatSessionContentModel
            contents = ChatSessionContentModel().get_contents_by_session(db_session_id)
            for c in contents:
                role = c.get("role", "user")
                content = c.get("content", "")
                if role == "user":
                    history.append(HumanMessage(content=content))
                elif role == "assistant":
                    history.append(AIMessage(content=content))
        except Exception as e:
            logger.error(f"加载数据库会话失败: {e}")
        return history

    def create_db_session(self, user_id: int, session_name: str = None) -> Optional[int]:
        """在数据库中创建会话，返回数据库会话 ID"""
        try:
            from sqlClass.chat_session_model import ChatSessionModel
            session_name = session_name or f"对话 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            return ChatSessionModel().add_session(user_id=user_id, session_name=session_name)
        except Exception as e:
            logger.error(f"创建数据库会话失败: {e}")
            return None

    def update_db_session(self, db_session_id: int, name: str = None, user_id: int = None) -> int:
        """更新数据库会话信息（名称 / 所属用户）"""
        from sqlClass.chat_session_model import ChatSessionModel
        return ChatSessionModel().update_session(db_session_id, name=name, user_id=user_id)

    def get_db_session(self, db_session_id: int) -> Optional[Dict[str, Any]]:
        """获取单条数据库会话记录"""
        from sqlClass.chat_session_model import ChatSessionModel
        return ChatSessionModel().get_session_by_id(db_session_id)

    def get_latest_db_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户最后一个数据库会话"""
        from sqlClass.chat_session_model import ChatSessionModel
        return ChatSessionModel().get_latest_session_by_user(user_id)

    def list_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的会话列表（长记忆）"""
        from sqlClass.chat_session_model import ChatSessionModel
        return ChatSessionModel().get_sessions_by_user(user_id)

    def count_user_sessions(self, user_id: int) -> int:
        return len(self.list_sessions(user_id))

    def get_db_messages(self, db_session_id: int) -> List[Dict[str, Any]]:
        """获取数据库会话的原始消息记录"""
        from sqlClass.chat_session_model import ChatSessionContentModel
        return ChatSessionContentModel().get_contents_by_session(db_session_id)

    def delete_db_session(self, db_session_id: int) -> None:
        """删除会话及其所有消息"""
        from sqlClass.chat_session_model import ChatSessionModel, ChatSessionContentModel
        ChatSessionContentModel().delete_contents_by_session(db_session_id)
        ChatSessionModel().delete_session(db_session_id)

    def restore_session(self, session_id: str, user_id: int = None) -> Dict[str, Any]:
        """从数据库恢复会话（或创建新会话）并写入短记忆

        支持 session_id 形如 ``sess_<db_id>`` 的历史会话恢复；
        若未找到历史会话且提供了 user_id，则新建数据库会话。
        """
        db_session_id = None
        history: List[BaseMessage] = []

        if session_id.startswith("sess_"):
            try:
                possible_db_id = int(session_id.split("_", 1)[1])
                from sqlClass.chat_session_model import ChatSessionModel
                if ChatSessionModel().get_session_by_id(possible_db_id):
                    db_session_id = possible_db_id
                    history = self.load_history(db_session_id)
                    logger.info(f"从数据库加载会话 {db_session_id}，共 {len(history)} 条历史消息")
            except (ValueError, TypeError):
                pass  # 不是 sess_<数字> 格式，继续创建新会话
            except Exception as e:
                logger.error(f"加载数据库会话失败: {e}")

        if not db_session_id and user_id:
            db_session_id = self.create_db_session(user_id)

        session_data = {
            "chat_history": history,
            "status": "initialized",
            "created_at": int(time.time()),
            "db_session_id": db_session_id,
            "question_count": 0,
        }
        self._sessions[session_id] = session_data
        return session_data

    def ensure_db_session(self, session_id: str, user_id: int) -> Optional[int]:
        """确保会话有对应的数据库记录，返回 db_session_id"""
        db_session_id = self.get_db_session_id(session_id)
        if db_session_id:
            try:
                self.update_db_session(db_session_id, user_id=int(user_id))
            except Exception as e:
                logger.debug(f"更新会话用户失败: {e}")
            return db_session_id
        db_session_id = self.create_db_session(user_id)
        self.set_db_session_id(session_id, db_session_id)
        return db_session_id


# 全局单例，供 web_app 等模块共享
memory = AgentMemory()
