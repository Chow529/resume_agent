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
from pathlib import Path

# 确保可以导入项目根目录的模块
project_root = Path(__file__).parent.parent  # 从 backend/ 回到项目根目录
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from langchain_core.messages import HumanMessage, AIMessage
import asyncio


# 导入（所有模块都在项目根目录下）
from rag.ChromaServer import ChromaServer
from agent.tools import agent_tools
from model.MoelFactory import ChatModelIni
from utils.readyml_tool import load_yaml_config
from utils.logging_tool import logger
from typing import Dict, Any, Optional
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
    """初始化一个会话，同时创建数据库中的会话记录"""
    session_data = {
        "chat_history": [],
        "status": "initialized",
        "created_at": int(time.time()),
        "db_session_id": None  # 数据库中的会话ID
    }
    _global_sessions[session_id] = session_data

    # 同时在数据库中创建会话记录
    try:
        from sqlClass.chat_session_model import ChatSessionModel
        chat_session_model = ChatSessionModel()
        db_session_id = chat_session_model.create_session(
            user_id=0,  # 0 表示未登录用户，登录后会更新
            session_name=f"会话_{session_id[:8]}"
        )
        if db_session_id:
            session_data["db_session_id"] = db_session_id
    except Exception as e:
        logger.debug(f"创建会话记录失败: {e}")  # 不记录为错误，因为可能是表不存在


def get_last_ai_message(messages):
    """从消息列表中获取最后一条 AI 回复消息"""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None


def save_message_to_db(session_id: str, role: str, content: str):
    """
    保存单条消息到数据库
    role: "user" 或 "assistant"
    """
    try:
        session = _global_sessions.get(session_id)
        if not session:
            return

        db_session_id = session.get("db_session_id")
        if not db_session_id:
            return

        from sqlClass.chat_session_model import ChatSessionContentModel
        content_model = ChatSessionContentModel()
        content_model.add_content(
            session_id=db_session_id,
            role=role,
            content=content
        )
    except Exception as e:
        logger.debug(f"保存消息到数据库失败: {e}")


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
            if sess_id and sess_id in _global_sessions:
                _global_sessions[sess_id]["resume_text"] = resume_text

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
        if sess_id and sess_id in _global_sessions:
            _global_sessions[sess_id]["resume_text"] = resume.get("file_path", "")

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
# 主页面路由（保持原有功能）
# ─────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
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


@app.put("/api/sessions/{session_id}/user")
async def bind_session_user(session_id: str, request: Request):
    """
    将 user_id 绑定到会话，使 /start 和 /resume 能读取该用户的简历
    """
    data = await request.json()
    uid = data.get("user_id")
    if not uid:
        raise HTTPException(status_code=400, detail="缺少 user_id")
    if session_id not in _global_sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    _global_sessions[session_id]["user_id"] = int(uid)
    return {"success": True}


@app.post("/api/sessions/{session_id}/chat")
async def chat(session_id: str, request: Request):
    """对话接口 - 用户发送消息，Agent回复"""
    # 如果会话不存在，自动创建（容错处理，解决session过期问题）
    if session_id not in _global_sessions:
        _global_sessions[session_id] = {
            "chat_history": [],
            "status": "initialized",
            "created_at": int(time.time())
        }
        logger.debug(f"自动创建新会话: {session_id}")

    data = await request.json()
    user_message = data.get("message", "").strip()
    # print(user_message)

    # 保存用户消息到数据库（无论是否特殊命令）
    save_message_to_db(session_id, "user", user_message)

    if not user_message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    session = _global_sessions[session_id]
    # 将 user_id 绑定到会话（前端每次发消息时带上）
    uid = data.get("user_id")
    if uid:
        session["user_id"] = int(uid)

    # 处理特殊命令
    if user_message == "/start":
        try:
            session = _global_sessions[session_id]
            user_id = session.get("user_id")

            # 检查是否有 user_id
            if not user_id:
                save_message_to_db(session_id, "user", user_message)
                return {
                    "session_id": session_id,
                    "message": "[请先登录] 请先登录或注册用户，然后上传简历",
                    "role": "error",
                    "type": "error"
                }

            # 清理旧对话历史
            chat_history = session["chat_history"]
            chat_history.clear()

            # 保存用户消息到数据库
            save_message_to_db(session_id, "user", user_message)

            # 让 Agent 主导面试流程 - Agent 会自动调用 get_job_working() 获取简历
            chat_history.append(HumanMessage(content=f"开始面试，请先获取我的简历信息,我的user_id是{user_id}"))

            agent = get_agent()
            response = agent.invoke({"messages": chat_history})
            messages = response.get("messages", [])
            last_ai = get_last_ai_message(messages)
            ai_reply = last_ai.content if last_ai and isinstance(last_ai.content, str) else ""

            chat_history.append(AIMessage(content=ai_reply))
            session["status"] = "interviewing"

            # 保存 agent 回复到数据库
            save_message_to_db(session_id, "agent", ai_reply)

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
        # 保存用户消息
        save_message_to_db(session_id, "user", user_message)
        session["chat_history"] = []
        session["status"] = "terminated"
        end_msg = "面试已结束，可以输入 /start 重新开始"
        save_message_to_db(session_id, "agent", end_msg)
        return {
            "session_id": session_id,
            "message": end_msg,
            "role": "agent",
            "type": "interview_end"
        }

    elif user_message == "/history":
        # 保存用户消息
        save_message_to_db(session_id, "user", user_message)
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
        history_msg = f"\n--- 对话历史 ({len(chat_history)} 条) ---\n{message_text}\n---"
        save_message_to_db(session_id, "agent", history_msg)
        return {
            "session_id": session_id,
            "message": history_msg,
            "role": "agent",
            "type": "history"
        }

    elif user_message == "/clear":
        # 保存用户消息
        save_message_to_db(session_id, "user", user_message)
        session["chat_history"].clear()
        session["status"] = "initialized"
        clear_msg = "对话历史已清空。"
        save_message_to_db(session_id, "agent", clear_msg)
        return {
            "session_id": session_id,
            "message": clear_msg,
            "role": "agent",
            "type": "cleared"
        }

    elif user_message == "/resume":
        session = _global_sessions[session_id]
        user_id = session.get("user_id")
        
        # 检查是否有 user_id
        if not user_id:
            return {
                "session_id": session_id,
                "message": "[请先登录] 请先登录并上传简历",
                "role": "agent",
                "type": "resume"
            }

        # 从数据库获取该用户激活的简历
        from sqlClass.resume_model import ResumeModel
        resume_model = ResumeModel()
        active_resume = resume_model.get_active(user_id)

        if active_resume and active_resume.get("resume_text"):
            resume_text = active_resume["resume_text"]
            return {
                "session_id": session_id,
                "message": f"\n[简历内容]\n{resume_text}",
                "role": "agent",
                "type": "resume"
            }
        else:
            return {
                "session_id": session_id,
                "message": "[提示] 未找到激活的简历，请先上传并激活简历",
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


