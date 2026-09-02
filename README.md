# 面试模拟 Agent (Interview Agent)

基于 LangGraph + RAG 的智能面试模拟系统，支持 **Web 界面** 和 **终端交互** 两种使用方式，集成用户认证、简历管理、语音输入、会话持久化和知识库检索。

## 功能特性

- **用户认证系统**：注册/登录/登出，支持会话保持
- **简历管理**：上传 PDF/DOCX 简历（每人最多 3 份），自动激活与切换
- **语音识别**：基于 Web Speech API 的麦克风输入，支持 Chrome/Edge/Safari
- **多会话管理**：创建/重命名/删除对话历史，登录自动加载最近会话
- **智能面试流程**：Agent 自动获取简历 → 检索 JD → 生成面试问题 → 评估回答
- **RAG 知识库**：向量化存储 QA 条目，支持可视化管理（添加/删除/浏览）
- **终端交互**：无需浏览器，命令行直接体验 Agent 能力
- **MySQL 持久化**：用户、会话、消息、简历数据全量存储

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python) |
| Agent 框架 | LangChain + LangGraph |
| 数据库 | MySQL (PyMySQL) |
| 向量库 | ChromaDB |
| 大模型 | DeepSeek (可配置) |
| 前端框架 | Vue 3 (Composition API) + Pinia |
| 构建工具 | Vite 5 |
| 语音识别 | Web Speech API |
| 服务器 | Uvicorn (ASGI) |

## 项目结构

```
resume_agent/
├── backend/                         # 后端主程序
│   ├── web_app.py                   # FastAPI 主程序（Web 版入口）
│   ├── agent/
│   │   ├── run_agent.py             # 终端交互版入口
│   │   └── tools/
│   │       ├── agent_tools.py       # Agent 工具（简历获取、JD抓取）
│   │       └── zhaopin_scraper.py   # 招聘网站爬虫
│   ├── rag/
│   │   ├── ChromaServer.py          # ChromaDB 向量库管理
│   │   └── ModelServer.py           # 嵌入模型服务
│   ├── model/
│   │   └── MoelFactory.py           # 模型工厂
│   ├── prompt/
│   │   └── prompt.yml               # Agent 系统提示词
│   ├── manual/
│   │   ├── manual_to_vector.py      # 文档向量化处理
│   │   └── user_manual.md           # 用户手册（向量化源）
│   ├── sqlClass/
│   │   ├── chat_session_model.py    # 会话数据模型
│   │   ├── mysql_connector.py       # MySQL 连接管理
│   │   └── resume_model.py          # 简历数据模型
│   ├── sql/                         # 数据库建表 SQL
│   │   ├── users_*.sql
│   │   ├── chat_sessions_*.sql
│   │   ├── chat_session_contents_*.sql
│   │   └── user_resumes_*.sql
│   └── utils/
│       ├── file_utils.py
│       ├── logging_tool.py
│       ├── path_tool.py
│       └── readyml_tool.py         # YAML/PDF 读取
├── frontend/                        # Vue.js 前端
│   ├── index.html                   # Vite 入口 HTML
│   ├── package.json                 # 前端依赖定义
│   ├── vite.config.js               # Vite 构建配置
│   ├── DESIGN.md                    # UI 设计规范
│   ├── dist/                        # 构建产物（生产模式）
│   │   ├── index.html
│   │   └── assets/
│   │       ├── index-*.js
│   │       └── index-*.css
│   └── src/
│       ├── main.js                  # Vue 应用入口
│       ├── App.vue                  # 根组件
│       ├── api/
│       │   └── index.js             # 后端 API 封装（23 个接口）
│       ├── components/
│       │   ├── AuthModal.vue        # 登录/注册弹窗
│       │   ├── ChatPanel.vue        # 聊天主面板
│       │   ├── MessageItem.vue      # 单条消息组件
│       │   ├── Sidebar.vue          # 侧边栏（会话历史/快捷操作）
│       │   ├── VoiceModal.vue       # 语音识别弹窗
│       │   ├── HelpModal.vue        # 命令帮助弹窗
│       │   ├── UserManageModal.vue  # 用户信息管理弹窗
│       │   ├── UploadResumeModal.vue# 上传简历弹窗
│       │   ├── ManageResumeModal.vue# 管理简历弹窗
│       │   └── KbModal.vue          # 知识库管理弹窗
│       ├── composables/
│       │   └── useSpeechRecognition.js  # Web Speech API 封装
│       ├── stores/
│       │   ├── auth.js              # 用户认证状态
│       │   ├── session.js           # 会话管理状态
│       │   ├── chat.js              # 聊天消息状态
│       │   ├── knowledge.js         # 知识库状态
│       │   └── resume.js            # 简历管理状态
│       ├── styles/
│       │   └── index.css            # 全局样式
│       └── utils/
│           └── index.js             # 工具函数
├── .env_temple                      # 环境变量模板
├── requestments.txt                 # Python 依赖
└── README.md                        # 本文件
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+（前端开发/构建）
- MySQL 5.7+ / 8.0+
- 现代浏览器（Chrome 90+ / Edge 90+ / Safari 14+）

### 2. 克隆项目并安装后端依赖

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requestments.txt

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
pip install -r requestments.txt
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 配置数据库

创建 MySQL 数据库（默认库名 `dmmdb`，可在代码中修改）：

```sql
CREATE DATABASE IF NOT EXISTS dmmdb 
  DEFAULT CHARACTER SET utf8mb4 
  DEFAULT COLLATE utf8mb4_unicode_ci;
```

执行建表脚本（按顺序）：

```bash
mysql -u <用户名> -p <数据库名> < backend/sql/users_*.sql
mysql -u <用户名> -p <数据库名> < backend/sql/chat_sessions_*.sql
mysql -u <用户名> -p <数据库名> < backend/sql/chat_session_contents_*.sql
mysql -u <用户名> -p <数据库名> < backend/sql/user_resumes_*.sql
```

> 数据库连接信息在 `backend/sqlClass/mysql_connector.py` 中配置，请根据实际环境修改。

### 5. 配置环境变量

复制 `.env_temple` 为 `.env` 并填写实际值：

```bash
cp .env_temple .env
```

编辑 `.env` 文件：

```ini
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
EMBEDDING_MODE=BAAI/bge-large-zh-v1.5
```

### 6. 准备向量库

首次使用需初始化知识库（将 `user_manual.md` 向量化）：

```bash
cd backend
python manual/manual_to_vector.py
```

或使用 Web 界面的"知识库"功能手动添加 QA 条目。

---

## 启动方式

### 方式一：生产模式（推荐部署）

先构建前端，再由后端统一提供服务：

```bash
# 1. 构建前端
cd frontend
npm run build

# 2. 启动后端（自动服务前端构建产物）
cd ../backend
uvicorn web_app:app --host 127.0.0.1 --port 8000
```

浏览器访问：[http://127.0.0.1:8000](http://127.0.0.1:8000)

> 生产模式下，后端自动读取 `frontend/dist/` 中的构建产物，无需单独启动前端服务。

### 方式二：开发模式（前后端分离）

前端使用 Vite dev server（支持热更新），后端独立运行：

```bash
# 终端 1：启动后端
cd backend
uvicorn web_app:app --host 127.0.0.1 --port 8000 --reload

# 终端 2：启动前端开发服务器
cd frontend
npm run dev
```

前端访问：[http://localhost:5173](http://localhost:5173)

> Vite 已配置代理，`/api` 请求自动转发到后端 `http://localhost:8000`。

### 方式三：终端版（无需浏览器）

```bash
cd backend
python agent/run_agent.py
```

---

## 使用流程

1. **注册账号** → 填写用户名、邮箱、密码
2. **上传简历** → 支持 PDF/DOCX 格式，最多 3 份
3. **开始对话** → 点击 `/start` 快捷按钮启动面试
4. **查看历史** → 左侧边栏展示所有会话，支持重命名和删除
5. **知识库** → 点击顶部"知识库"入口管理 QA 条目

### 可用命令

| 命令 | Web 版 | 终端版 | 说明 |
|------|--------|--------|------|
| `/start` | yes | yes | 启动面试流程 |
| `/end` | yes | yes | 结束面试 |
| `/resume` | yes | yes | 查看当前简历内容 |
| `/vector 关键词` | yes | yes | 查询向量库中相关 JD 数量 |
| `/history` | yes | yes | 查看当前对话历史 |
| `/help` | yes | yes | 查看命令帮助 |
| `/quit` | — | yes | 退出终端 |

---

## API 接口

### 用户认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/logout` | 用户登出 |
| GET | `/api/auth/check` | 检查用户名/邮箱可用性 |
| GET | `/api/auth/me` | 获取用户信息 |
| PUT | `/api/auth/user/email` | 修改邮箱 |
| PUT | `/api/auth/user/password` | 修改密码 |

### 简历管理

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/api/resume/upload` | 上传简历（multipart/form-data） |
| GET | `/api/resume/list` | 获取简历列表 |
| DELETE | `/api/resume/{id}` | 删除简历 |
| PUT | `/api/resume/{id}/activate` | 激活指定简历 |

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sessions/list` | 获取用户所有会话 |
| GET | `/api/sessions/latest` | 获取最近会话及消息 |
| GET | `/api/sessions/{id}/messages` | 获取会话消息 |
| GET | `/api/sessions/{id}/status` | 获取会话状态 |
| GET | `/api/sessions/{id}/init` | 初始化会话 |
| PUT | `/api/sessions/{id}/user` | 绑定用户到会话 |
| POST | `/api/sessions/{id}/chat` | 发送消息到 Agent |
| PUT | `/api/sessions/{id}/rename` | 重命名会话 |
| DELETE | `/api/sessions/{id}/delete` | 删除会话 |

### 知识库管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/vector/manual/list` | 列出所有 QA 文档 |
| POST | `/api/vector/manual/add` | 添加 QA 文档 |
| DELETE | `/api/vector/manual/{id}` | 删除 QA 文档 |

---

## 公网访问（ngrok）

如需公网访问，可使用 ngrok 映射本地端口：

```bash
# 1. 安装 ngrok（Windows）
curl -L https://ngrok.s3.amazonaws.com/ngrok-windows-amd64-3.zip -o ngrok.zip

# 2. 配置 Authtoken
ngrok config add-authtoken <your_token>

# 3. 启动隧道
ngrok http 8000
```

获取 `https://xxx.ngrok-free.app` 地址即可外网访问。

---

## 常见问题

**Q: 启动时报 MySQL 连接失败？**
A: 检查 `backend/sqlClass/mysql_connector.py` 中的数据库连接配置，确保 MySQL 服务已启动，数据库 `dmmdb` 已创建。

**Q: Agent 初始化失败？**
A: 检查 `.env` 中的 `DEEPSEEK_API_KEY` 是否正确，网络是否可访问 API。

**Q: 语音输入不工作？**
A: Web Speech API 需要 HTTPS 环境或 localhost。确保使用 Chrome/Edge/Safari 最新版，首次使用需授权麦克风权限。

**Q: 知识库为空？**
A: 首次使用需执行向量化初始化（见"准备向量库"章节），之后可通过 Web UI 的"知识库"入口手动添加 QA 条目。

**Q: 登录后对话历史丢失？**
A: 会话数据存储在 MySQL，服务重启不影响。确保登录的是同一账号。

**Q: 前端构建失败？**
A: 确保 Node.js 版本 >= 18，在 `frontend/` 目录下执行 `npm install` 安装依赖后再执行 `npm run build`。

**Q: 后端启动后页面空白？**
A: 确保已执行 `npm run build` 生成 `frontend/dist/` 目录，后端会自动读取该目录下的构建产物。

**Q: 终端版找不到简历？**
A: 终端版使用本地文件路径 `job/jobhunter.pdf`，需手动放置简历文件。Web 版通过界面上传即可。

---

## 许可证

本项目采用 MIT 许可证。
