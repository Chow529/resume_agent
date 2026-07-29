"""
面试模拟 Agent - Web版 (FastAPI)
Web服务接口
"""
import os
import sys
import uuid
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# 确保可以导入项目根目录的模块
project_root = Path(__file__).parent.parent  # 从 backend/ 回到项目根目录
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from langchain_core.messages import HumanMessage, AIMessage
import asyncio

# 导入（所有模块都在项目根目录下）
from rag.ChromaServer import ChromaServer
from agent.tools import agent_tools
from model.MoelFactory import ChatModelIni
from utils.readyml_tool import load_yaml_config, load_pdf
from utils.logging_tool import logger

app = FastAPI(title="面试模拟 Agent Web版", version="1.0.0")

# 全局变量
_agent = None
_chroma_server = None
_global_sessions: Dict[str, Dict[str, Any]] = {}


# ─────────────────────────────────────────────────────
# 中间件：只记录核心 API 调用信息（方法、路径、状态码）
# ─────────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录每个 HTTP 请求的核心调用信息"""
    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        # 只记录调用信息，不打印详细错误
        logger.info(f"| {request.method} {request.url.path} | ERR | {elapsed_ms:.0f}ms")
        raise

    elapsed_ms = (time.time() - start_time) * 1000
    # 核心调用日志：方法 | 路径 | 状态码 | 耗时
    logger.info(f"| {request.method} {request.url.path} | {response.status_code} | {elapsed_ms:.0f}ms")

    return response


# ─────────────────────────────────────────────────────
# 会话管理辅助函数
# ─────────────────────────────────────────────────────
def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def get_chroma_server():
    global _chroma_server
    if _chroma_server is None:
        _chroma_server = ChromaServer()
    return _chroma_server


def build_agent():
    """构建Agent实例"""
    prompt = load_yaml_config("prompt/prompt.yml")
    if prompt is None:
        raise FileNotFoundError("未找到 prompt/prompt.yml 配置文件")
    system_prompt = prompt.get("MAIN_PROMPT", "")
    from langchain.agents import create_agent
    chat_model = ChatModelIni().InitModel()
    agent = create_agent(
        chat_model,
        tools=[agent_tools.get_job_working, agent_tools.get_jd_content],
        system_prompt=system_prompt,
    )
    return agent


def init_session(session_id: str):
    """初始化一个会话"""
    _global_sessions[session_id] = {
        "chat_history": [],
        "status": "initialized",
        "created_at": int(time.time())
    }


def get_last_ai_message(messages):
    """从消息列表中获取最后一条 AI 回复消息"""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None

@app.get("/favicon.ico")
async def favicon():
    """提供网站图标 favicon.ico"""
    icon_path = project_root / "frontend" / "static" / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path, media_type="image/x-icon")
    # 如果找不到，返回空响应（浏览器会显示默认图标）
    return Response(content="", status_code=404)

# ─────────────────────────────────────────────────────
# API 路由
# ─────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    """主页面 - 面试模拟器"""
    session_id = str(uuid.uuid4())
    init_session(session_id)
    html_path = project_root / "frontend" / "index.html"
    html_content = html_path.read_text(encoding="utf-8")
    html_content = html_content.replace("{SESSION_ID}", session_id)
    return html_content


@app.get("/api/sessions/{session_id}/init")
async def init_session_endpoint(session_id: str):
    """初始化会话端点"""
    if session_id not in _global_sessions:
        _global_sessions[session_id] = {
            "chat_history": [],
            "status": "initialized",
            "created_at": int(time.time())
        }
    return {"session_id": session_id, "status": "initialized"}


@app.post("/api/sessions/{session_id}/chat")
async def chat(session_id: str, request: Request):
    """对话接口 - 用户发送消息，Agent回复"""
    if session_id not in _global_sessions:
        raise HTTPException(status_code=404, detail="会话不存在")

    data = await request.json()
    user_message = data.get("message", "").strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    session = _global_sessions[session_id]

    # 处理特殊命令
    if user_message == "/start":
        try:
            user_resum = load_pdf()
            if not user_resum:
                return {
                    "session_id": session_id,
                    "message": "[错误] 未找到简历文件，请先将简历放入 job/jobhunter.pdf",
                    "role": "error"
                }

            chat_history = session["chat_history"]
            chat_history.clear()
            chat_history.append(HumanMessage(content="开始面试，请先获取我的简历信息"))

            agent = get_agent()
            response = agent.invoke({"messages": chat_history})
            messages = response.get("messages", [])
            last_ai = get_last_ai_message(messages)
            ai_reply = last_ai.content if last_ai else ""

            chat_history.append(AIMessage(content=ai_reply))
            session["status"] = "interviewing"

            return {
                "session_id": session_id,
                "message": ai_reply,
                "role": "agent",
                "type": "interview_start"
            }
        except Exception as e:
            logger.error(f"Agent执行错误: {e}")
            return {
                "session_id": session_id,
                "message": f"[错误] Agent执行失败: {str(e)}",
                "role": "error"
            }

    elif user_message == "/end":
        session["chat_history"] = []
        session["status"] = "terminated"
        return {
            "session_id": session_id,
            "message": "面试已结束，可以输入 /start 重新开始",
            "role": "agent",
            "type": "interview_end"
        }

    elif user_message == "/history":
        chat_history = session["chat_history"]
        if not chat_history:
            message_text = "暂无对话历史。"
        else:
            lines = []
            for i, msg in enumerate(chat_history, 1):
                role = "用户" if isinstance(msg, HumanMessage) else "Agent"
                content = msg.content[:100] if isinstance(msg.content, str) else str(msg.content)[:100]
                lines.append(f"  {i}. [{role}] {content}...")
            message_text = "\n".join(lines)
        return {
            "session_id": session_id,
            "message": f"\n--- 对话历史 ({len(chat_history)} 条) ---\n{message_text}\n---",
            "role": "agent",
            "type": "history"
        }

    elif user_message == "/clear":
        session["chat_history"].clear()
        session["status"] = "initialized"
        return {
            "session_id": session_id,
            "message": "对话历史已清空。",
            "role": "agent",
            "type": "cleared"
        }

    elif user_message == "/resume":
        user_resum = load_pdf()
        if user_resum:
            content = "\n".join([doc.page_content for doc in user_resum])
            return {
                "session_id": session_id,
                "message": f"\n[简历内容]\n{content}",
                "role": "agent",
                "type": "resume"
            }
        else:
            return {
                "session_id": session_id,
                "message": "[提示] 未找到简历文件 job/jobhunter.pdf",
                "role": "agent",
                "type": "resume_not_found"
            }

    elif user_message.startswith("/vector"):
        try:
            retriever = get_chroma_server().get_retriever()
            jd_parts = [x.strip() for x in user_message.split(" ") if x.strip()]
            if len(jd_parts) > 1:
                all_docs = retriever.invoke(jd_parts[-1])
                return {
                    "session_id": session_id,
                    "message": f"\n[向量库] 当前存储了 {len(all_docs)} 条相关JD记录",
                    "role": "agent",
                    "type": "vector"
                }
            else:
                return {
                    "session_id": session_id,
                    "message": "请提供查询关键词，例如: /vector python",
                    "role": "agent",
                    "type": "vector"
                }
        except Exception as e:
            return {
                "session_id": session_id,
                "message": f"[向量库] 查询失败: {str(e)}",
                "role": "error"
            }

    # 普通对话 - 交给Agent处理
    chat_history = session["chat_history"]
    chat_history.append(HumanMessage(content=user_message))

    try:
        agent = get_agent()
        response = agent.invoke({"messages": chat_history})
        messages = response.get("messages", [])
        last_ai = get_last_ai_message(messages)
        ai_reply = last_ai.content if last_ai else ""
        chat_history.append(AIMessage(content=ai_reply))

        return {
            "session_id": session_id,
            "message": ai_reply,
            "role": "agent"
        }
    except Exception as e:
        logger.error(f"Agent执行错误: {e}", exc_info=True)
        return {
            "session_id": session_id,
            "message": f"[错误] Agent执行失败: {str(e)}",
            "role": "error"
        }


@app.get("/api/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """获取会话状态"""
    if session_id not in _global_sessions:
        _global_sessions[session_id] = {
            "chat_history": [],
            "status": "initialized",
            "created_at": int(time.time())
        }
    return {"session_id": session_id, "status": _global_sessions[session_id]["status"]}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if session_id in _global_sessions:
        del _global_sessions[session_id]
    return {"status": "ok", "session_id": session_id}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "timestamp": int(time.time())}
