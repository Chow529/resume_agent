"""
面试模拟 Agent - Web版 (FastAPI)
Web服务接口
"""
import os
import sys
import uuid
import time
import logging
import io
import tempfile
import mimetypes
from pathlib import Path

# 修复 Windows 注册表缺少 MIME 类型导致 JS 文件以 text/plain 返回的问题
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/javascript', '.mjs')
mimetypes.add_type('text/css', '.css')

# 确保可以导入项目根目录的模块
project_root = Path(__file__).parent.parent  # 从 backend/ 回到项目根目录
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 添加 sqlClass 目录到路径
sql_class_dir = Path(__file__).parent / "sqlClass"
if str(sql_class_dir) not in sys.path:
    sys.path.insert(0, str(sql_class_dir))

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response, StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage,ToolMessage
import asyncio


# 导入（所有模块都在项目根目录下）
from rag.ChromaServer import ChromaServer
from agent.tools.agent_tools import tool_registry
from agent.memory import memory
from model.MoelFactory import ChatModelIni, reload_models, config_ready
from utils.readyml_tool import load_yaml_config
from utils.logging_tool import logger
from typing import Optional
# ========== 意图识别配置 ==========
# 从 intent.yml 加载，使用关键字匹配判断用户意图
_intent_config = load_yaml_config("prompt/intent.yml") or {}
# 意图为 other 时的对话边界约束，确保回答不偏离项目范围
_boundary_prompt = (load_yaml_config("prompt/prompt.yml") or {}).get("BOUNDARY_PROMPT", "")
# 帮助意图：基于知识库检索内容回答用户问题的提示词
_help_prompt = (load_yaml_config("prompt/prompt.yml") or {}).get("HELP_PROMPT", "")


def _match_intent(message: str) -> Optional[str]:
    """基于关键字识别用户意图，未匹配任何意图时返回 "other"""
    msg_lower = message.strip().lower()
    for intent, conf in (_intent_config.get("intents") or {}).items():
        commands = [c.lower() for c in (conf.get("commands") or [])]
        keywords = [k.lower() for k in (conf.get("keywords") or [])]
        # 精确匹配指令
        if msg_lower in commands:
            return intent
        # 关键字包含匹配
        for kw in keywords:
            if kw in msg_lower:
                return intent
    return "other"

app = FastAPI(title="面试模拟 Agent Web版", version="1.0.0")

# 全局变量
_agent = None
_chroma_server = None


@app.on_event("startup")
async def _ensure_db_schema():
    """启动时幂等迁移：为 chat_sessions 补上面试状态字段（status / question_count）。
    数据库不可用时不阻断服务启动。"""
    try:
        from sqlClass.chat_session_model import ChatSessionModel
        await asyncio.to_thread(ChatSessionModel().ensure_interview_columns)
        logger.info("面试状态字段迁移检查完成")
    except Exception as e:
        logger.warning(f"面试状态字段迁移跳过（数据库暂不可用？）: {e}")


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

# 每个会话的取消事件（按 session_id 隔离），用于用户主动结束推理
_session_cancel_events: dict[str, "threading.Event"] = {}
# 每个会话当前正在执行的 agent 后台线程（便于取消后等待退出）
_session_agent_threads: dict[str, "threading.Thread"] = {}


def _get_cancel_event(session_id: str) -> "threading.Event":
    """获取（或创建）该会话的取消事件。新会话默认未取消。"""
    import threading as _t
    ev = _session_cancel_events.get(session_id)
    if ev is None:
        ev = _t.Event()
        _session_cancel_events[session_id] = ev
    return ev


def _sse(event: str, data: dict) -> str:
    """构造一条 SSE 消息"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def reload_agent():
    """清除全局 Agent 缓存，下次调用 get_agent() 时根据最新 config.json 重建"""
    global _agent
    _agent = None
    reload_models()


def get_chroma_server():
    global _chroma_server
    if _chroma_server is None:
        _chroma_server = ChromaServer()
    return _chroma_server


def build_agent():
    """构建 Agent（LangGraph 版本）"""
    prompt = load_yaml_config("prompt/prompt.yml")
    if prompt is None:
        raise FileNotFoundError("未找到 prompt/prompt.yml 配置文件")
    system_prompt = prompt.get("MAIN_PROMPT", "")
    
    chat_model = ChatModelIni().InitModel().bind_tools(
        tool_registry.get_tool_func()
    )

    from langgraph.graph import StateGraph, START, END
    from langgraph.prebuilt import ToolNode
    from typing import TypedDict, Annotated
    from langgraph.graph.message import add_messages

    class InterviewState(TypedDict):
        messages: Annotated[list, add_messages]
        state: str

    def call_model(state):
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        return {"messages": [chat_model.invoke(messages)]}

    def should_continue(state):
        if isinstance(state["messages"][-1], AIMessage) and state["messages"][-1].tool_calls:
            # print(state["messages"][-1])
            return "tools"
        return END

    graph = StateGraph(InterviewState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tool_registry.get_tool_func()))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def init_session(session_id: str):
    """初始化一个会话（仅内存，不创建数据库记录）。数据库会话在用户登录绑定后由 bind_session_user 创建。"""
    memory.init_session(session_id)


def save_message_to_db(session_id: str, role: str, content: str):
    """保存单条消息到数据库（长记忆）"""
    memory.save_message(session_id, role, content)


# 定义常用邮箱后缀
COMMON_EMAIL_SUFFIXES = {
    'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
    'qq.com', '163.com', '126.com', 'sina.com', 'sohu.com',
    'foxmail.com', 'aliyun.com', 'tom.com', 'yeah.net',
    'icloud.com', 'me.com', 'protonmail.com', 'proton.me'
}

def validate_email(email: str) -> bool:
    # 1. 必须包含 @
    if '@' not in email :
        return False

    if email.count('@') != 1:
        return False
    
    # 2. 获取 @ 后面的域名
    domain = email.split('@')[1].lower()
    
    # 3. 检查是否在常用后缀列表中
    if domain not in COMMON_EMAIL_SUFFIXES:
        return False
    
    return True

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

# ─────────────────────────────────────────────────────
# 用户认证相关接口
# ─────────────────────────────────────────────────────

# 导入用户模型（使用正确的导入路径，因为项目根目录已在sys.path中）
# 注意：实际导入在 get_user_model() 函数内部进行，以避免循环导入问题
import hashlib
import secrets
from fastapi import Form, HTTPException

# 创建全局用户模型实例（使用默认的数据库连接）
user_model = None

def get_user_model():
    """获取或创建用户模型实例"""
    global user_model
    if user_model is None:
        # 在函数内部导入，避免路径问题
        from sqlClass.mysql_connector import UserModel
        user_model = UserModel()
    return user_model


def hash_password(password: str, salt: str) -> str:
    """
    使用SHA-256+盐值进行密码哈希
    实际生产环境建议使用bcrypt或PBKDF2
    """
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()


@app.post("/api/auth/login")
async def login(request: Request):
    """
    用户登录接口
    - 验证用户名和密码
    - 验证账户是否被锁定或禁用
    - 记录登录尝试次数
    - 登录成功后返回用户ID
    """
    try:
        # 解析JSON请求体
        data = await request.json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return {"success": False, "message": "用户名和密码不能为空", "userId": None}

        model_db = get_user_model()

        # 1. 从数据库中查询用户
        user = model_db.get_user_by_username(username)
        if not user:
            return {"success": False, "message": "用户名或密码错误", "userId": None}

        # 2. 检查账户状态
        if user.get('is_active', 0) == 0:
            return {"success": False, "message": "账户已被禁用", "userId": None}
        if user.get('is_locked', 0) == 1:
            return {"success": False, "message": "账户已被锁定，请联系管理员", "userId": None}

        # 3. 验证密码（对比密码哈希）
        salt = user.get('salt', '')
        if not salt:
            return {"success": False, "message": "用户数据不完整", "userId": None}

        expected_hash = user.get('password_hash', '')
        actual_hash = hash_password(password, salt)

        if actual_hash != expected_hash:
            # 密码错误，更新失败尝试次数
            failed_attempts = user.get('failed_login_attempts', 0) + 1
            last_failed = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

            # 如果尝试次数超过5次，锁定账户
            if failed_attempts >= 5:
                model_db.update(user['id'], {'failed_login_attempts': failed_attempts, 'last_failed_login_at': last_failed, 'is_locked': 1})
                return {"success": False, "message": "账号已因多次失败登录被锁定，请联系管理员", "userId": None}

            model_db.update(user['id'], {'failed_login_attempts': failed_attempts, 'last_failed_login_at': last_failed})
            return {"success": False, "message": "用户名或密码错误", "userId": None}

        # 4. 登录成功，重置失败尝试次数，更新最后登录时间
        model_db.update(user['id'], {
            'failed_login_attempts': 0,
            'last_failed_login_at': None,
            'is_locked': 0,
            'last_login_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        })

        # 5. 返回用户ID
        return {"success": True, "message": "登录成功", "userId": user['id']}

    except Exception as e:
        logger.error(f"登录错误: {e}")
        return {"success": False, "message": "服务器内部错误", "userId": None}


@app.post("/api/auth/register")
async def register(request: Request):
    """
    用户注册接口
    - 检查用户名和邮箱是否已存在
    - 生成盐值（salt）和密码哈希（password_hash）
    - 创建新用户记录
    - 注册成功后自动登录
    """
    print("注册请求处理中...")
    try:
        # 解析JSON请求体
        data = await request.json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return {"success": False, "message": "所有字段都是必填的", "userId": None}

        # 验证输入长度
        if len(username) < 5 or len(username) > 50:
            return {"success": False, "message": "用户名长度必须在5-50个字符之间", "userId": None}

        if len(password) < 8:
            return {"success": False, "message": "密码长度至少为8位", "userId": None}

        model_db = get_user_model()

        # 1. 检查用户名是否已存在
        if model_db.get_user_by_username(username):
            return {"success": False, "message": "用户名已被占用", "userId": None}

        # 2. 检查邮箱是否已存在
        if model_db.get_user_by_email(email):
            return {"success": False, "message": "该邮箱已被注册", "userId": None}

        # 3. 生成随机盐值
        salt = secrets.token_hex(32)  # 64字符的十六进制字符串

        # 4. 使用PBKDF2-like方式对密码进行哈希处理
        password_hash = hash_password(password, salt)

        # 5. 插入新用户记录
        user_id = model_db.create_user(username, email, password_hash, salt)
        if user_id is None:
            return {"success": False, "message": "注册失败，请重试", "userId": None}

        # 6. 返回userId（登录状态）
        return {"success": True, "message": "注册成功", "userId": user_id}

    except Exception as e:
        logger.error(f"注册错误: {e}")
        return {"success": False, "message": "服务器内部错误", "userId": None}


@app.get("/api/auth/check")
async def check_user_available(field: str = None, value: str = None):
    """
    检查用户名或邮箱是否可用
    - 字段（field）可以是"username"或"email"
    - 返回可用状态和消息
    """
    if not field or not value:
        return {"available": False, "message": "缺少参数"}

    # 验证field参数
    if field not in ['username', 'email']:
        return {"available": False, "message": "无效的字段名，只能是username或email"}

    try:
        model_db = get_user_model()

        # 从数据库中检查该字段对应的值是否已存在
        if field == 'username':
            user = model_db.get_user_by_username(value)
        else:  # email
            user = model_db.get_user_by_email(value)

        if user:
            # 返回更具体的消息，便于前端展示
            if field == 'username':
                return {"available": False, "message": "用户名已被占用"}
            else:  # email
                return {"available": False, "message": "该邮箱已被注册"}
        else:
            return {"available": True, "message": f"{field}可用"}

    except Exception as e:
        logger.error(f"检查可用性问题: {e}")
        return {"available": False, "message": "系统繁忙，请稍后重试"}


@app.post("/api/auth/logout")
async def logout(request: Request):
    """
    用户登出接口
    - 清除用户的session状态
    - 可以在token黑名单中记录
    """
    # TODO: 实际生产环境中这里应该清理服务端会话状态
    # 例如：将JWT加入黑名单，或清除Redis中的session数据
    return {"success": True, "message": "已登出"}


@app.get("/api/auth/me")
async def get_current_user(user_id: str = None):
    """
    获取当前登录用户信息
    - 返回用户的用户名、邮箱等基本信息
    """
    if not user_id:
        return {"userId": None, "username": "", "email": "", "createdAt": ""}

    try:
        model_db = get_user_model()
        # 根据用户ID获取用户信息
        user = model_db.get(int(user_id))
        if not user:
            return {"userId": user_id, "username": "", "email": "", "createdAt": ""}

        return {
            "userId": str(user['id']),
            "username": user['username'],
            "email": user['email'],
            "createdAt": user.get('created_at', '')
        }
    except Exception as e:
        logger.error(f"获取用户信息错误: {e}")
        return {"userId": user_id, "username": "", "email": "", "createdAt": ""}


@app.put("/api/auth/user/email")
async def update_user_email(request: Request):
    """
    修改用户邮箱
    - 需要用户ID和新邮箱
    - 检查新邮箱是否已被其他用户使用
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        new_email = data.get('email')

        if not user_id or not new_email:
            return {"success": False, "message": "用户ID和邮箱都是必填的"}

        # 验证邮箱格式
        if not (('@' in new_email) ):
            return {"success": False, "message": "邮箱格式无效"}

        db = get_user_model()

        # 检查新邮箱是否已被占用（排除当前用户）
        user = db.get(int(user_id))
        if not user:
            return {"success": False, "message": "用户不存在"}

        existing_users = db.get_all_by('email', new_email)
        if existing_users and existing_users[0]['id'] != int(user_id):
            return {"success": False, "message": "该邮箱已被注册"}

        # 更新邮箱
        db.update(int(user_id), {'email': new_email})
        return {"success": True, "message": "邮箱修改成功"}

    except Exception as e:
        logger.error(f"修改邮箱错误: {e}")
        return {"success": False, "message": "服务器内部错误"}


@app.put("/api/auth/user/password")
async def update_user_password(request: Request):
    """
    修改用户密码
    - 需要用户ID、旧密码和新密码
    - 验证旧密码正确性
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not user_id or not old_password or not new_password:
            return {"success": False, "message": "所有字段都是必填的"}

        if len(new_password) < 8:
            return {"success": False, "message": "新密码长度至少为8位"}

        db = get_user_model()

        # 获取用户信息
        user = db.get(int(user_id))
        if not user:
            return {"success": False, "message": "用户不存在"}

        # 验证旧密码
        salt = user.get('salt', '')
        if not salt:
            return {"success": False, "message": "用户数据不完整"}

        expected_hash = user.get('password_hash', '')
        actual_hash = hash_password(old_password, salt)

        if actual_hash != expected_hash:
            return {"success": False, "message": "旧密码错误"}

        # 生成新盐值和密码哈希
        new_salt = secrets.token_hex(32)
        new_password_hash = hash_password(new_password, new_salt)

        # 更新密码
        db.update(int(user_id), {
            'password_hash': new_password_hash,
            'salt': new_salt
        })

        return {"success": True, "message": "密码修改成功"}

    except Exception as e:
        logger.error(f"修改密码错误: {e}")
        return {"success": False, "message": "服务器内部错误"}


# ─────────────────────────────────────────────────────
# 简历管理 API（新接口）
# ─────────────────────────────────────────────────────


@app.put("/api/resume/upload")
async def upload_resume(request: Request):
    """
    上传简历文件
    - 接收 multipart/form-data，字段名 file
    - 仅允许 .pdf 和 .docx 格式
    - 文件大小限制：10MB
    - 保存原始文件到文件系统，并存储解析后的文本到数据库
    - 新上传的简历自动激活，同时取消该用户其他所有简历的激活状态
    - 每个用户最多 3 份简历（总数量，不论激活状态）
    """
    try:
        form = await request.form()
        file_obj = form.get("file")
        if not file_obj or not hasattr(file_obj, "read"):
            raise HTTPException(status_code=400, detail="缺少文件参数")

        user_id = request.query_params.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="缺少 user_id 参数")

        # 获取文件名并验证格式
        try:
            filename = file_obj.filename
        except Exception:
            filename = ""

        if not filename:
            raise HTTPException(status_code=400, detail="缺少文件名")

        filename_lower = filename.lower()
        if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".docx")):
            raise HTTPException(status_code=400, detail="仅支持 .pdf 和 .docx 格式")

        # 读取文件内容以检查大小
        raw_bytes = await file_obj.read()
        file_size = len(raw_bytes)
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")

        # 使用 markitdown 解析文本（先解析，失败则无需保存文件）
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert_stream(
            io.BytesIO(raw_bytes),
            file_extension=filename_lower.split(".")[-1]
        )
        resume_text = result.text_content if result else ""
        # print(f"resume_text: {resume_text}, raw_bytes: {len(raw_bytes)}")
        if not resume_text or not resume_text.strip():
            # 提取失败：可能是扫描件（图片型 PDF）、空文件、或损坏的文件
            raise HTTPException(
                status_code=400,
                detail=f"无法从文件中提取文本内容。该文件可能为扫描件（图片型 PDF），不含可提取的文本。请使用文本型 PDF 或 Word 文档（.pdf/.docx）上传，扫描版 PDF 可先用 OCR 工具转换为文本格式"
            )

        # 先检查数据库上限（避免数据库操作失败后产生孤立文件）
        from sqlClass.resume_model import ResumeModel
        resume_model = ResumeModel()
        if resume_model.count_total(int(user_id)) >= 3:
            raise HTTPException(status_code=400, detail="上传失败：已达到简历数量上限（3份）")

        # 生成临时文件路径（用于原子写入）
        upload_dir = project_root / "uploads" / str(user_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        temp_file = upload_dir / f".tmp_{uuid.uuid4()}_{filename_lower}"

        try:
            # 1. 写入临时文件
            with open(temp_file, "wb") as f:
                f.write(raw_bytes)

            # 2. 保存到数据库
            resume_id = resume_model.create(
                user_id=int(user_id),
                filename=filename_lower,
                file_path="",  # 临时为空，稍后更新
                resume_text=resume_text
            )

            if resume_id is None:
                raise RuntimeError("数据库保存失败（create返回None）")

            # 3. 将临时文件重命名为正式文件（原子操作）
            final_file = upload_dir / filename_lower
            if final_file.exists():
                # 如果目标文件已存在，删除它
                final_file.unlink()
            temp_file.rename(final_file)

            # 4. 更新数据库中的 file_path
            resume_model.update(resume_id, {'file_path': str(final_file)})

            # 5. 激活新上传的简历（同时取消该用户其他所有简历的激活状态）
            resume_model.set_active(int(user_id), resume_id)

            # 更新当前会话的 resume_text（如果提供了 session_id）
            sess_id = request.query_params.get("session_id")
            if sess_id and memory.has_session(sess_id):
                memory.set_resume_text(sess_id, resume_text)

            return {
                "success": True,
                "message": "简历上传成功并激活",
                "resume_id": resume_id,
                "filename": filename,
                "file_type": filename_lower.split(".")[-1]
            }

        except Exception as e:
            # 清理临时文件（如果存在）
            if temp_file.exists():
                temp_file.unlink()
            raise HTTPException(status_code=500, detail=f"上传过程中发生错误: {str(e)}")


    except HTTPException:
        raise
    except Exception as e:
        # 检查是否是客户端断开连接（用户取消上传）
        try:
            from starlette.requests import ClientDisconnect
            if isinstance(e, ClientDisconnect):
                logger.info("客户端上传中断")
                return {"success": False, "message": "上传已中断"}
        except ImportError:
            pass

        logger.error(f"简历上传错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)[:200]}")


@app.get("/api/resume/list")
async def list_resumes(request: Request):  # noqa: ARG001
    """列出用户所有激活的简历"""
    user_id = request.query_params.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="缺少 user_id 参数")

    try:
        from sqlClass.resume_model import ResumeModel
        resume_model = ResumeModel()
        all_resumes = resume_model.get_all(int(user_id))

        # 只返回激活的
        # active_resumes = [r for r in all_resumes if r.get("is_active", 1) == 1]

        return {
            "success": True,
            "count": len(all_resumes),
            "resumes": [
                {
                    "id": r["id"],
                    "filename": r["filename"],
                    "uploaded_at": str(r.get("uploaded_at", "")),
                    "is_active": r.get("is_active", 0)
                }
                for r in all_resumes
            ]
        }
    except Exception as e:
        logger.error(f"获取简历列表错误: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.delete("/api/resume/{resume_id}")
async def delete_resume(resume_id: int):
    """删除简历（逻辑删除，同时删除原始文件）"""
    try:
        from sqlClass.resume_model import ResumeModel
        resume_model = ResumeModel()

        resume = resume_model.get_by_id(resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="简历不存在")

        # 先删除原始文件（如果存在）
        file_path = resume.get("file_path", "")
        if file_path:
            from utils.file_utils import delete_resume_file
            delete_resume_file(file_path)

        # 逻辑删除文件
        resume_model.deactivate(resume_id)

        return {
            "success": True,
            "message": f"简历 '{resume['filename']}' 已删除"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除简历错误: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.put("/api/resume/{resume_id}/activate")
async def activate_resume(resume_id: int, request: Request):
    """
    激活指定简历（同时取消该用户其他简历的激活状态）
    """
    try:
        from sqlClass.resume_model import ResumeModel
        resume_model = ResumeModel()

        resume = resume_model.get_by_id(resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="简历不存在")

        user_id = resume["user_id"]
        # 先取消该用户的所有激活，再激活指定简历
        resume_model.set_active(user_id, resume_id)

        # 更新当前会话的 resume_text
        sess_id = request.query_params.get("session_id")
        if sess_id and memory.has_session(sess_id):
            memory.set_resume_text(sess_id, resume.get("file_path", ""))

        return {
            "success": True,
            "message": f"已切换为使用 '{resume['filename']}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"激活简历错误: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


# ─────────────────────────────────────────────────────
# 主页面路由（Vue SPA 构建产物）
# ─────────────────────────────────────────────────────

# Vue SPA 构建产物目录
_DIST_DIR = project_root / "frontend" / "dist"

# 挂载静态资源目录（JS/CSS 等）
if (_DIST_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(_DIST_DIR / "assets")), name="static-assets")


@app.get("/", response_class=HTMLResponse)
async def index():
    session_id = str(uuid.uuid4())
    init_session(session_id)
    # 优先使用 Vue SPA 构建产物，回退到原始 index.html（开发模式）
    html_path = _DIST_DIR / "index.html"
    if not html_path.exists():
        html_path = project_root / "frontend" / "index.html"
    html_content = html_path.read_text(encoding="utf-8")
    html_content = html_content.replace("{SESSION_ID}", session_id)
    return html_content


@app.get("/api/sessions/{session_id}/init")
async def init_session_endpoint(session_id: str, user_id: int = Query(None)):
    """初始化会话端点 - 从数据库恢复历史会话，或创建新的数据库会话记录"""
    if not memory.has_session(session_id):
        memory.restore_session(session_id, user_id)
    # 返回数据库恢复出的真实面试状态（initialized/interviewing/terminated），
    # 而非硬编码 initialized，保证面试中途退出后重新登录能回到面试模式
    return {
        "session_id": session_id,
        "status": memory.get_status(session_id),
        "question_count": memory.get_question_count(session_id),
        "db_session_id": memory.get_db_session_id(session_id),
    }


@app.put("/api/sessions/{session_id}/user")
async def bind_session_user(session_id: str, request: Request):
    """
    将 user_id 绑定到会话，使 /start 和 /resume 能读取该用户的简历
    如果数据库会话不存在，则创建一个新的
    """
    data = await request.json()
    uid = data.get("user_id")
    if not uid:
        raise HTTPException(status_code=400, detail="缺少 user_id")
    if not memory.has_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    memory.set_user_id(session_id, int(uid))

    # 确保数据库会话存在
    db_session_id = memory.ensure_db_session(session_id, int(uid))
    if not db_session_id:
        return {"success": False, "message": "创建会话失败"}

    return {"success": True, "db_session_id": db_session_id}


@app.post("/api/sessions/{session_id}/chat")
async def chat(session_id: str, request: Request):
    """对话接口 - 流式版（SSE）

    事件类型：
    - chunk:          增量内容 {content}
    - done:           推理完成 {content, type, role, db_session_id}
    - cancelled:      用户主动取消 {content, type, db_session_id}
    - error:          出错 {message, db_session_id}
    - config_required: AI 模型未配置 {message, db_session_id}
    """
    if not memory.has_session(session_id):
        memory.restore_session(session_id)
        logger.debug(f"创建/加载会话: {session_id}, db_session_id: {memory.get_db_session_id(session_id)}")

    data = await request.json()
    user_message = data.get("message", "").strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    if not config_ready():
        async def cfg_required_stream():
            yield _sse("config_required", {
                "session_id": session_id,
                "message": "[AI 模型未配置] 请先完成 AI 模型配置后再使用该功能",
                "db_session_id": None,
            })
        return StreamingResponse(cfg_required_stream(), media_type="text/event-stream")

    uid = data.get("user_id")
    if uid:
        memory.set_user_id(session_id, int(uid))

    if not memory.get_db_session_id(session_id) and memory.get_user_id(session_id):
        db_session_id = memory.ensure_db_session(session_id, memory.get_user_id(session_id))
        logger.info(f"自动创建数据库会话: {db_session_id}")

    # 保存用户消息到数据库（无论是否特殊命令）
    save_message_to_db(session_id, "user", user_message)

    # ── 意图识别 ──
    intent = _match_intent(user_message)
    print(intent)
        
    # 准备：direct_reply 直接回复（无需 agent），agent_messages 走流式推理
    direct_reply = None
    agent_messages = None
    response_type = intent if intent else "other"
    post_status = None              # 推理完成后要设置的 session 状态
    clear_history_after = False    # 推理完成后是否清空历史

    if intent == "start_interview":
        user_id = memory.get_user_id(session_id)
        if not user_id:
            direct_reply = "[请先登录] 请先登录或注册用户，然后上传简历"
            response_type = "error"
        else:
            memory.clear_history(session_id)
            # 立即把状态落库为 interviewing，不必等首轮回复完成，
            # 防止首轮推理过程中用户退出导致状态仍停留在旧值
            memory.set_status(session_id, "interviewing")
            memory.add_user_message(session_id, f"开始面试，请先获取我的简历信息,我的user_id是{user_id}")
            agent_messages = memory.get_history(session_id)
            post_status = "interviewing"
            response_type = "interview_start"

    elif intent == "end_interview":
        memory.clear_history(session_id)
        memory.set_status(session_id, "terminated")
        direct_reply = "面试已结束，可以输入 /start 重新开始"
        response_type = "interview_end"

    elif intent == "view_resume":
        user_id = memory.get_user_id(session_id)
        if not user_id:
            direct_reply = "[请先登录] 请先登录并上传简历"
            response_type = "resume"
        else:
            from sqlClass.resume_model import ResumeModel
            resume_model = ResumeModel()
            active_resume = resume_model.get_active(user_id)
            if active_resume and active_resume.get("resume_text"):
                direct_reply = f"\n[简历内容]\n{active_resume['resume_text']}"
                response_type = "resume"
            else:
                direct_reply = "[提示] 未找到激活的简历，请先上传并激活简历"
                response_type = "resume_not_found"

    elif intent == "query_vector":
        try:
            retriever = get_chroma_server().get_retriever()
            jd_parts = [x.strip() for x in user_message.split(" ") if x.strip()]
            if len(jd_parts) > 1:
                all_docs = retriever.invoke(jd_parts[-1])
                direct_reply = f"\n[向量库] 当前存储了 {len(all_docs)} 条相关JD记录"
            else:
                direct_reply = "请提供查询关键词，例如: /vector python"
            response_type = "vector"
        except Exception as e:
            direct_reply = f"[向量库] 查询失败: {str(e)}"
            response_type = "error"

    elif intent == "help":
        agent_messages = memory.build_prompt_messages(
            session_id,
            extra_messages=[HumanMessage(content=user_message)],
            system_prefix=_help_prompt,
        )
        response_type = "help"

    else:
        # 普通对话
        memory.trim_history(session_id)
        memory.add_user_message(session_id, user_message)
        current_round = memory.increment_question_count(session_id)
        boundary = _boundary_prompt if intent == "other" else None
        print(current_round)
        if current_round >= 11:
            extra = [HumanMessage(content="以上是我全部的回答,请根据我的回答以及我的表现,给出综合汇总评价以及评分。")]
            agent_messages = memory.build_prompt_messages(session_id, extra_messages=extra, system_prefix=boundary)
            post_status = "terminated"
            clear_history_after = True
            response_type = "interview_end"
        else:
            agent_messages = memory.build_prompt_messages(session_id, system_prefix=boundary)

    # 重置当前会话的取消事件（按 session_id 隔离，多会话互不干扰）
    cancel_event = _get_cancel_event(session_id)
    cancel_event.clear()

    db_session_id = memory.get_db_session_id(session_id)

    async def event_stream():
        # 分支 1：直接回复（无需 agent）
        if direct_reply is not None:
            yield _sse("chunk", {"content": direct_reply})
            save_message_to_db(session_id, "assistant", direct_reply)
            if post_status:
                memory.set_status(session_id, post_status)
            yield _sse("done", {
                "content": direct_reply,
                "type": response_type,
                "role": "agent",
                "db_session_id": db_session_id,
            })
            return

        # 分支 2：agent 流式推理
        if agent_messages is None:
            yield _sse("error", {"message": "无可执行的推理流程", "db_session_id": db_session_id})
            return

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()
        import threading as _t

        def run_agent():
            """后台线程：迭代 agent.stream，把 chunks 通过 queue 传回异步侧"""
            try:
                agent = get_agent()
                for chunk in agent.stream({"messages": agent_messages}, stream_mode="messages"):
                    if cancel_event.is_set():
                        loop.call_soon_threadsafe(queue.put_nowait, {"type": "cancelled"})
                        return
                    # stream_mode="messages" 时 chunk 是 (message, metadata) 元组
                    if not isinstance(chunk, tuple) or len(chunk) < 2:
                        continue
                    msg, metadata = chunk[0], chunk[1]
                    # 只输出 agent 节点（模型调用）产生的 AIMessage 文本内容。
                    # langgraph 在 stream_mode="messages" 下会对同一消息 yield 多次
                    # （作为某节点的输出，又作为下一节点的输入），所以必须用
                    # metadata["langgraph_node"] 限定只取 "agent" 节点产生的消息，
                    # 否则 ToolMessage 等工具返回结果会被重复输出到界面。
                    if metadata.get("langgraph_node") != "agent":
                        continue
                    # 跳过工具调用消息（含 tool_calls 时 content 通常为空字符串）
                    if getattr(msg, "tool_calls", None):
                        continue
                    if isinstance(msg, ToolMessage):
                        continue
                    content = getattr(msg, "content", "")
                    if not content or not isinstance(content, str):
                        continue
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "chunk", "content": content})
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "done"})
            except Exception as e:
                logger.error(f"Agent 流式执行错误: {e}", exc_info=True)
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})

        thread = _t.Thread(target=run_agent, daemon=True)
        _session_agent_threads[session_id] = thread
        thread.start()

        full_reply = ""
        # 标记是否已经把 full_reply 保存到长/短记忆（避免重复保存）
        saved = False

        async def _save_reply(status_tag: str = None):
            """把已生成的 full_reply 写入长记忆（数据库）+ 短记忆（上下文）"""
            nonlocal saved
            if saved or not full_reply:
                return
            saved = True
            content = full_reply + (f"\n[{status_tag}]" if status_tag else "")
            try:
                memory.add_ai_message(session_id, content)
                save_message_to_db(session_id, "assistant", content)
            except Exception as e:
                logger.error(f"保存流式回复失败: {e}", exc_info=True)

        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    if not thread.is_alive():
                        break
                    continue

                t = item.get("type")
                if t == "chunk":
                    full_reply += item["content"]
                    yield _sse("chunk", {"content": item["content"]})
                elif t == "done":
                    # 推理正常完成：保存完整回复
                    await _save_reply()
                    if post_status:
                        memory.set_status(session_id, post_status)
                    if clear_history_after:
                        memory.clear_history(session_id)
                    yield _sse("done", {
                        "content": full_reply,
                        "type": response_type,
                        "role": "agent",
                        "db_session_id": db_session_id,
                    })
                    return
                elif t == "cancelled":
                    # 用户主动取消：保存已生成的部分（带停止标记）
                    await _save_reply(status_tag="已停止")
                    yield _sse("cancelled", {
                        "content": full_reply,
                        "type": response_type,
                        "db_session_id": db_session_id,
                    })
                    return
                elif t == "error":
                    err_msg = f"[错误] Agent执行失败: {item['message']}"
                    save_message_to_db(session_id, "assistant", err_msg)
                    yield _sse("error", {"message": err_msg, "db_session_id": db_session_id})
                    return
        finally:
            # 客户端断开或异常退出：通知线程停止并等待退出
            cancel_event.set()
            thread.join(timeout=2.0)
            cancel_event.clear()
            _session_agent_threads.pop(session_id, None)
            # 兜底：若异常路径下尚未保存（如客户端在流式过程中断开），也要落库
            # 保证已生成的 partial 内容不会丢失到长期记忆
            if not saved and full_reply:
                try:
                    memory.add_ai_message(session_id, full_reply)
                    save_message_to_db(session_id, "assistant", full_reply)
                except Exception as e:
                    logger.error(f"客户端断开后保存流式回复失败: {e}", exc_info=True)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/sessions/{session_id}/cancel")
async def cancel_chat(session_id: str):
    """取消指定会话正在进行的推理（按 session_id 隔离，互不干扰）"""
    ev = _get_cancel_event(session_id)
    ev.set()
    return {"success": True, "session_id": session_id}


# ─────────────────────────────────────────────────────
# 向量库管理 API（user_manual 可视化）
# ─────────────────────────────────────────────────────
_chroma_manual = None
@app.get("/api/vector/manual/list")
async def list_manual_documents():
    """列出 user_manual 向量库中所有文档"""
    try:
        if _chroma_manual is None:
            _chroma_manual = ChromaServer(chromaType="user_manual")
        documents = _chroma_manual.list_all_documents()
        
        # 统计信息
        sections = {}
        for doc in documents:
            metadata = doc.get('metadata') or {}
            section = metadata.get('section', '未知')
            sections[section] = sections.get(section, 0) + 1
        
        return {
            "success": True,
            "total": len(documents),
            "sections": sections,
            "documents": documents
        }
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        return {"success": False, "message": f"获取文档列表失败: {str(e)}"}


@app.post("/api/vector/manual/add")
async def add_manual_document(request: Request):
    """添加 QA 文档到 user_manual 向量库"""
    try:
        data = await request.json()
        question = data.get("question", "").strip()
        answer = data.get("answer", "").strip()
        section = data.get("section", "自定义")
        q_id = data.get("q_id", "")
        
        # 验证 QA 格式
        if not question or not answer:
            return {"success": False, "message": "问题和答案都不能为空"}
        
        if len(question) < 2:
            return {"success": False, "message": "问题内容过短，请提供完整的问题描述"}
        
        if len(answer) < 2:
            return {"success": False, "message": "答案内容过短，请提供完整的回答"}
        
        # 自动生成 q_id（如果未提供）
        if not q_id:
            if _chroma_manual is None:
                _chroma_manual = ChromaServer(chromaType="user_manual")
            existing_docs = _chroma_manual.list_all_documents()
            max_num = 0
            for doc in existing_docs:
                doc_id = doc.get('id', '')
                if doc_id.startswith('Q') and doc_id[1:].isdigit():
                    num = int(doc_id[1:])
                    if num > max_num:
                        max_num = num
            q_id = f"Q{max_num + 1}"
        
        if _chroma_manual is None:
            _chroma_manual = ChromaServer(chromaType="user_manual")
        success = _chroma_manual.add_qa_document(q_id, question, answer, section)
        
        if success:
            return {"success": True, "message": "文档添加成功", "q_id": q_id}
        else:
            return {"success": False, "message": "文档添加失败，请重试"}
    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        return {"success": False, "message": f"添加文档失败: {str(e)}"}


@app.delete("/api/vector/manual/{doc_id}")
async def delete_manual_document(doc_id: str):
    """删除 user_manual 向量库中的文档"""
    try:
        if _chroma_manual is None:
            _chroma_manual = ChromaServer(chromaType="user_manual")
        success = _chroma_manual.delete_document(doc_id)
        
        if success:
            return {"success": True, "message": f"文档 {doc_id} 已删除"}
        else:
            return {"success": False, "message": f"删除文档 {doc_id} 失败"}
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        return {"success": False, "message": f"删除文档失败: {str(e)}"}


@app.get("/api/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """获取会话状态（内存未命中时先从数据库恢复，避免后端重启后状态丢失）"""
    if not memory.has_session(session_id):
        memory.restore_session(session_id)
    return {
        "session_id": session_id,
        "status": memory.get_status(session_id),
        "question_count": memory.get_question_count(session_id),
    }


@app.get("/api/sessions/list")
async def list_user_sessions(user_id: int = Query(None)):
    """获取用户的所有会话列表"""
    if not user_id:
        return {"success": False, "message": "缺少 user_id", "sessions": []}
    try:
        sessions = memory.list_sessions(user_id)
        result = []
        for s in sessions:
            result.append({
                'id': s['id'],
                'session_name': s.get('session_name', f'会话_{s["id"]}'),
                'created_at': str(s.get('created_at', '')),
                'updated_at': str(s.get('updated_at', s.get('created_at', '')))
            })
        return {"success": True, "sessions": result}
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        return {"success": False, "message": str(e), "sessions": []}


@app.get("/api/sessions/{db_session_id}/messages")
async def get_session_messages(db_session_id: int):
    """获取指定会话的所有消息"""
    try:
        contents = memory.get_db_messages(db_session_id)
        messages = []
        for c in contents:
            role = c.get('role', 'user')
            if role == 'assistant':
                role = 'agent'
            messages.append({
                'role': role,
                'content': c.get('content', ''),
                'created_at': str(c.get('created_at', ''))
            })
        return {"success": True, "messages": messages}
    except Exception as e:
        logger.error(f"获取会话消息失败: {e}")
        return {"success": False, "message": str(e), "messages": []}


@app.put("/api/sessions/{db_session_id}/rename")
async def rename_session(db_session_id: int, request: Request):
    """重命名会话（同一用户下重名自动追加 _1）"""
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        return {"success": False, "message": "名称不能为空"}
    try:
        session = memory.get_db_session(db_session_id)
        if not session:
            return {"success": False, "message": "会话不存在"}
        user_id = session.get("user_id")
        if user_id:
            others = [s.get("session_name") for s in memory.list_sessions(user_id) if s.get("id") != db_session_id]
            final_name, n = name, 1
            while final_name in others:
                final_name = f"{name}_{n}"
                n += 1
            name = final_name
        memory.update_db_session(db_session_id, name=name)
        return {"success": True, "message": "已重命名", "name": name}
    except Exception as e:
        logger.error(f"重命名会话失败: {e}")
        return {"success": False, "message": str(e)}


@app.delete("/api/sessions/{db_session_id}/delete")
async def delete_session(db_session_id: int):
    """删除指定会话及其所有消息（至少保留一条对话）"""
    try:
        session = memory.get_db_session(db_session_id)
        if not session:
            return {"success": False, "message": "会话不存在"}
        # 若该用户只有这一条会话，拒绝删除，保证历史列表至少保留一条
        user_id = session.get("user_id")
        if user_id and memory.count_user_sessions(user_id) <= 1:
            return {"success": False, "message": "至少保留一条对话，无法删除"}
        memory.delete_db_session(db_session_id)
        return {"success": True, "message": "会话已删除"}
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        return {"success": False, "message": str(e)}


@app.get("/api/sessions/latest")
async def get_latest_session(user_id: int = Query(None)):
    """获取用户最后一个会话及其消息"""
    if not user_id:
        return {"success": False, "message": "缺少 user_id", "session": None, "messages": []}
    try:
        # 获取用户最后一个会话
        latest_session = memory.get_latest_db_session(user_id)

        if not latest_session:
            return {"success": True, "has_session": False, "message": "暂无历史会话", "session": None, "messages": []}

        # 获取该会话的消息
        contents = memory.get_db_messages(latest_session['id'])

        messages = []
        for c in contents:
            role = c.get('role', 'user')
            if role == 'assistant':
                role = 'agent'
            messages.append({
                'role': role,
                'content': c.get('content', ''),
                'created_at': str(c.get('created_at', ''))
            })

        return {
            "success": True,
            "has_session": True,
            "session": {
                'id': latest_session['id'],
                'session_name': latest_session.get('session_name', f'会话_{latest_session["id"]}'),
                'created_at': str(latest_session.get('created_at', ''))
            },
            "messages": messages
        }
    except Exception as e:
        logger.error(f"获取最后会话失败: {e}")
        return {"success": False, "message": str(e), "session": None, "messages": []}


# ─────────────────────────────────────────────────────
# AI 模型配置管理 API
# ─────────────────────────────────────────────────────
import json

CONFIG_FILE = project_root / "config.json"


@app.get("/api/config/status")
async def get_config_status():
    """返回当前是否已完成 AI 模型配置"""
    ready = config_ready()
    return {"success": True, "ready": ready}


@app.get("/api/config/load")
async def load_config():
    """从 config.json 加载已保存的模型配置"""
    if not CONFIG_FILE.is_file():
        return {"success": True, "config": None, "message": "暂无已保存的配置"}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        return {"success": True, "config": config}
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        return {"success": False, "message": f"读取配置失败: {str(e)}"}


@app.post("/api/config/test")
async def test_config(request: Request):
    """测试模型连接

    仅调用提供商的模型列表接口（GET /models）做连通性与鉴权校验，
    不发起对话补全请求，因此不会消耗 token。
    """
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return {"success": False, "message": "请求数据格式错误"}

    model_name = (data.get("model_name") or "").strip()
    api_key = (data.get("api_key") or "").strip()
    base_url = (data.get("base_url") or "").strip()

    if not model_name or not api_key or not base_url:
        return {"success": False, "message": "模型名称、API Key、Base URL 均不能为空"}

    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, timeout=15)
        # GET /models 只校验接口连通性与 API Key，不产生 token 消耗
        models = llm.root_client.models.list()
        model_ids = [m.id for m in models.data]
        return {
            "success": True,
            "message": "连接成功，接口与 API Key 校验通过（本次测试未消耗 token）",
            "model_count": len(model_ids),
            "model_found": model_name in model_ids,
        }
    except Exception as e:
        logger.error(f"测试模型连接失败: {e}")
        return {"success": False, "message": f"连接失败: {str(e)[:300]}"}


@app.post("/api/config/save")
async def save_config(request: Request):
    """保存模型配置到 config.json，并重新加载后端模型实例"""
    try:
        data = await request.json()
        config = {
            "provider": data.get("provider", "openai"),
            "model_name": data.get("model_name", ""),
            "api_key": data.get("api_key", ""),
            "base_url": data.get("base_url", ""),
            "temperature": data.get("temperature", 0.7),
            "max_tokens": data.get("max_tokens", 4096),
            "embedding_model": data.get("embedding_model", ""),
            "embedding_separate": data.get("embedding_separate", False),
            "embedding_provider": data.get("embedding_provider", "openai"),
            "embedding_api_key": data.get("embedding_api_key", ""),
            "embedding_base_url": data.get("embedding_base_url", ""),
        }
        if not config["model_name"]:
            return {"success": False, "message": "模型名称不能为空"}
        if not config["api_key"]:
            return {"success": False, "message": "API Key 不能为空"}
        if not config["base_url"]:
            return {"success": False, "message": "Base URL 不能为空"}
        try:
            temp = float(config["temperature"])
            if not (0 <= temp <= 2):
                return {"success": False, "message": "温度值需在 0~2 之间"}
        except (ValueError, TypeError):
            return {"success": False, "message": "温度值必须为数字"}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        # 重新加载模型实例，使新配置立即生效
        reload_agent()
        return {"success": True, "message": "配置已保存，模型已重新加载"}
    except json.JSONDecodeError:
        return {"success": False, "message": "请求数据格式错误"}
    except Exception as e:
        logger.error(f"保存配置失败: {e}", exc_info=True)
        return {"success": False, "message": f"保存失败: {str(e)}"}


@app.post("/api/config/reset")
async def reset_config(request: Request):
    """重置配置：删除 config.json，清除模型缓存"""
    try:
        if CONFIG_FILE.is_file():
            CONFIG_FILE.unlink()
        reload_agent()
        return {"success": True, "message": "配置已重置，请重新完成 AI 模型配置"}
    except Exception as e:
        logger.error(f"重置配置失败: {e}")
        return {"success": False, "message": f"重置失败: {str(e)}"}


# ─────────────────────────────────────────────────────
# SPA 路由回退（必须放在所有 API 路由之后）
# ─────────────────────────────────────────────────────
@app.get("/{path:path}", response_class=HTMLResponse)
async def spa_fallback(path: str):
    if path.startswith("api/") or path.startswith("assets/"):
        raise HTTPException(status_code=404, detail="Not Found")
    file_path = _DIST_DIR / path
    if file_path.is_file():
        return FileResponse(file_path)
    return await index()


if __name__ == "__main__":
    import uvicorn
    
    # uvicorn.run(app, reload=True,host="127.0.0.1", port=8000)
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=True)

