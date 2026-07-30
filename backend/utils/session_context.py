"""
线程局部上下文 - 用于在 LangChain agent invoke 调用链中传递 session 信息
"""
import threading

_thread_local = threading.local()


def set_current_session(session_id: str, resume_text: str = ""):
    """设置当前线程的会话信息（在调用 agent.invoke() 前调用）"""
    _thread_local.session_id = session_id
    _thread_local.resume_text = resume_text


def get_current_session():
    """获取当前线程的会话信息（在 agent tool 内部调用）"""
    return {
        "session_id": getattr(_thread_local, "session_id", ""),
        "resume_text": getattr(_thread_local, "resume_text", ""),
    }


def clear():
    """清理当前线程的会话信息"""
    _thread_local.session_id = ""
    _thread_local.resume_text = ""
