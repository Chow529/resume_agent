# 面试模拟 Agent (Interview Agent)

基于 LangGraph + RAG 的智能面试模拟系统，支持 **Web 界面** 和 **终端交互** 两种使用方式，集成用户认证、简历管理、语音输入、会话持久化、岗位 JD 采集、知识库检索和在线模型配置。

## 功能特性

- **AI 模型在线配置**：通过 Web 界面配置大模型（支持任意 OpenAI 兼容接口），保存后立即生效，无需重启
- **用户认证系统**：注册/登录/登出，支持会话保持、账户锁定保护
- **简历管理**：上传 PDF/DOCX 简历（每人最多 3 份），自动解析文本、激活与切换
- **语音识别**：基于 Web Speech API 的麦克风输入，识别结果自动回填输入框，支持 Chrome/Edge/Safari
- **多会话管理**：创建/重命名/删除对话历史，登录自动加载最近会话；多会话可并发推理、独立缓存消息，支持随时停止生成
- **智能面试流程**：可选岗（从数据中心 JD 中选定目标岗位）或由 Agent 自动获取简历 → 检索 JD → 生成面试问题 → 综合评分
- **岗位 JD 数据中心**：模块化采集器架构，内置智联招聘采集；爬取岗位详情页补全「岗位职责/任职要求」；支持个人 JD 与公用 JD、岗位使用排名
- **RAG 知识库**：向量化存储 QA 条目，支持可视化管理（添加/删除/浏览）
- **终端交互**：无需浏览器，命令行直接体验 Agent 能力
- **MySQL 持久化**：用户、会话、消息、简历、岗位 JD 数据全量存储

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python) |
| Agent 框架 | LangChain + LangGraph |
| 数据库 | MySQL (PyMySQL) |
| 向量库 | ChromaDB |
| 大模型 | 任意 OpenAI 兼容接口（通过 Web UI 配置） |
| 前端框架 | Vue 3 (Composition API) + Pinia |
| 构建工具 | Vite 5 |
| 语音识别 | Web Speech API |
| 简历解析 | MarkItDown |
| 岗位爬虫 | curl_cffi（模拟 Chrome TLS 指纹绕过反爬） |
| 服务器 | Uvicorn (ASGI) |

## 项目结构

```
resume_agent/
├── backend/                            # 后端主程序
│   ├── web_app.py                      # FastAPI 主程序（Web 版入口）
│   ├── agent/
│   │   ├── memory.py                   # 会话记忆（短记忆上下文 + 长记忆落库）
│   │   ├── run_agent.py                # 终端交互版入口
│   │   └── tools/
│   │       ├── agent_tools.py          # Agent 工具（简历获取、JD 获取、教程获取）
│   │       └── tool_Servers.py         # 工具注册表
│   ├── collectors/                     # 岗位数据采集（可扩展）
│   │   ├── base.py                     # 采集器基类 / 参数定义 / 结果结构
│   │   ├── registry.py                 # 采集器注册表
│   │   ├── zhaopin_collector.py        # 智联招聘采集器
│   │   └── tools/
│   │       └── zhaopin_scraper.py      # 智联招聘爬虫（列表页 + 详情页）
│   ├── routers/
│   │   └── data_center.py              # 数据中心路由（模块元数据 / 采集 / JD 管理）
│   ├── rag/
│   │   ├── ChromaServer.py             # ChromaDB 向量库管理
│   │   └── ModelServer.py              # 嵌入模型 & 摘要服务
│   ├── model/
│   │   └── MoelFactory.py              # 模型工厂（从 config.json 加载）
│   ├── prompt/
│   │   ├── prompt.yml                  # 系统提示词（面试/闲聊边界/帮助/摘要等）
│   │   └── intent.yml                  # 意图识别配置（命令与关键词）
│   ├── manual/
│   │   ├── manual_to_vector.py         # 文档向量化处理
│   │   ├── user_manual.md              # 用户手册（向量化源）
│   │   └── QA.md                       # QA 知识条目
│   ├── sqlClass/
│   │   ├── mysql_connector.py          # MySQL 连接管理 & 用户模型
│   │   ├── chat_session_model.py       # 会话 & 消息模型
│   │   ├── resume_model.py             # 简历数据模型
│   │   └── job_jd_model.py             # 岗位 JD 数据模型
│   ├── sql/                            # 建表脚本（按文件名序号执行）
│   │   ├── users_202607301412_1.sql
│   │   ├── chat_sessions_202607301412_2.sql
│   │   ├── chat_session_contents_202607301411_3.sql
│   │   ├── job_jds_202609111800_4.sql
│   │   └── user_resumes_sql.sql
│   └── utils/
│       ├── file_utils.py               # 文件操作
│       ├── logging_tool.py             # 日志工具
│       ├── path_tool.py                # 路径工具
│       └── readyml_tool.py             # YAML/PDF 读取
├── frontend/                           # Vue.js 前端
│   ├── index.html                      # Vite 入口 HTML
│   ├── package.json                    # 前端依赖定义
│   ├── vite.config.js                  # Vite 构建配置
│   ├── DESIGN.md                       # UI 设计规范
│   ├── static/
│   │   └── favicon.ico                 # 网站图标
│   └── src/
│       ├── main.js                     # Vue 应用入口
│       ├── App.vue                     # 根组件
│       ├── api/
│       │   └── index.js                # 后端 API 封装（37 个接口）
│       ├── components/
│       │   ├── AuthModal.vue           # 登录/注册弹窗
│       │   ├── ChatPanel.vue           # 聊天主面板
│       │   ├── MessageItem.vue         # 单条消息组件
│       │   ├── Sidebar.vue             # 侧边栏（会话历史/快捷操作）
│       │   ├── VoiceModal.vue          # 语音识别弹窗
│       │   ├── HelpModal.vue           # 命令帮助弹窗
│       │   ├── UserManageModal.vue     # 用户信息管理弹窗
│       │   ├── UploadResumeModal.vue   # 上传简历弹窗
│       │   ├── ManageResumeModal.vue   # 管理简历弹窗
│       │   ├── KbModal.vue             # 知识库管理弹窗
│       │   ├── ModelConfigModal.vue    # AI 模型配置弹窗
│       │   ├── DataCenterModal.vue     # 数据中心弹窗（岗位 JD 采集与管理）
│       │   ├── JDSelectModal.vue       # 开始面试时选择目标岗位弹窗
│       │   └── data-center/            # 采集模块前端（按后端元数据动态渲染）
│       │       ├── registry.js         # 模块 UI 注册表
│       │       └── ZhaopinModule.vue   # 智联招聘模块（采集表单/JD 列表/详情）
│       ├── composables/
│       │   └── useSpeechRecognition.js # Web Speech API 封装
│       ├── stores/
│       │   ├── auth.js                 # 用户认证状态
│       │   ├── session.js              # 会话管理状态
│       │   ├── chat.js                 # 聊天消息状态
│       │   ├── knowledge.js            # 知识库状态
│       │   ├── resume.js               # 简历管理状态
│       │   └── config.js               # 模型配置状态
│       ├── styles/
│       │   └── index.css               # 全局样式
│       └── utils/
│           ├── index.js                # 工具函数
│           └── events.js               # 全局事件总线
├── config.json                         # AI 模型配置（通过 Web UI 生成）
├── .env                                # 环境变量（数据库连接等，参考 .env_temple）
├── .env_temple                         # 环境变量模板
├── requestments.txt                    # Python 依赖
└── README.md                           # 本文件
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

在项目根目录创建 `.env`（可复制 `.env_temple`），配置 MySQL 连接：

```ini
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=你的密码
DB_LIBRARY=agent_db
DB_PORT=3306
```

创建数据库：

```sql
CREATE DATABASE IF NOT EXISTS agent_db
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
```

按序号执行 `backend/sql/` 下的建表脚本：

```bash
mysql -u <用户名> -p agent_db < backend/sql/users_202607301412_1.sql
mysql -u <用户名> -p agent_db < backend/sql/chat_sessions_202607301412_2.sql
mysql -u <用户名> -p agent_db < backend/sql/chat_session_contents_202607301411_3.sql
mysql -u <用户名> -p agent_db < backend/sql/job_jds_202609111800_4.sql
mysql -u <用户名> -p agent_db < backend/sql/user_resumes_sql.sql
```

> 连接参数由 `.env` 提供，代码中通过 `os.getenv` 读取，默认库名见 `backend/sqlClass/mysql_connector.py`。

### 5. 准备向量库（可选）

首次使用可初始化知识库（将 `user_manual.md` 向量化）：

```bash
cd backend
python manual/manual_to_vector.py
```

也可稍后通过 Web 界面的"知识库"功能手动添加 QA 条目。

### 6. 启动服务

参见下方 [启动方式](#启动方式) 章节。首次启动后，通过 Web 界面完成 **AI 模型配置** 即可开始使用（无需手动编辑配置文件）。

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
python ./web_app.py
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

1. **配置 AI 模型**：首次使用需点击顶部"模型配置"，填写模型名称、API Key、Base URL（支持 DeepSeek / OpenAI / 其他兼容接口），保存后立即生效
2. **注册账号** → 填写用户名、邮箱、密码
3. **上传简历** → 支持 PDF/DOCX 格式，最多 3 份，自动解析文本
4. **采集岗位 JD（可选）** → 顶部"数据中心"选择采集模块（如智联招聘），按城市 + 岗位关键词爬取，结果按用户入库
5. **开始对话** → 点击 `/start` 或"开始面试"，从个人/公用 JD 中选择目标岗位后开始
6. **查看历史** → 左侧边栏展示所有会话，支持重命名和删除
7. **知识库** → 点击顶部"知识库"入口管理 QA 条目

### 可用命令

| 命令 | Web 版 | 终端版 | 说明 |
|------|--------|--------|------|
| `/start` | yes | yes | 启动面试流程 |
| `/end` | yes | yes | 结束面试 |
| `/resume` | yes | yes | 查看当前简历内容 |
| `/vector 关键词` | yes | yes | 查询向量库中相关 JD 数量 |
| `/help` | yes | yes | 查看命令帮助 |
| `/quit` | — | yes | 退出终端 |

> Web 版同时支持自然语言触发（由 `prompt/intent.yml` 配置），例如"开始面试""结束面试""查看简历""查询 JD"等。

---

## 数据中心与岗位采集

数据中心提供岗位 JD 的采集、管理与复用能力，入口为顶部"数据中心"。

### 采集流程

1. 选择采集模块（当前内置 **智联招聘**）
2. 填写参数：工作城市、岗位关键词（多个用英文逗号分隔）、爬取时间预算
3. 后端流式推送采集进度（SSE），完成后按 `user_id` 写入 `job_jds` 表

采集时除列表页字段外，还会抓取**岗位详情页**补全「岗位职责 / 任职要求」；若详情缺失则回退列表页摘要或结构化字段兜底，保证 JD 内容可用于面试提问。

### 个人数据与公用数据

| 类型 | 可见范围 | 说明 |
|------|----------|------|
| 个人 JD | 仅本人 | 默认状态，可在数据中心查看/删除 |
| 公用 JD | 所有用户 | 由个人数据主动公开，**公开后不可改回个人数据** |

### 岗位排名

- **个人排名**：本人 JD 按被选为面试岗位的使用次数降序
- **公用排名**：所有用户公开的 JD 按使用次数汇总（按来源 + 来源岗位 ID 合并）降序

### 扩展新采集模块

采集器采用注册表 + 后端元数据驱动前端渲染，新增来源只需：

1. 新建采集器文件，继承 `BaseCollector` 并实现 `scrape()`；
2. 用 `@register_collector` 注册，并在 `collectors/__init__.py` 中 import 一次；
3. 前端数据中心会自动通过 `/api/data-center/modules` 拿到新模块与参数表单定义。

> 若采集的仍是"岗位 JD"类数据，直接映射为 `job_jds` 行即可，无需改表；全新数据类型再新建表与 Model 类（一表一类）。

---

## AI 模型配置

系统通过项目根目录的 `config.json` 管理模型配置，支持通过 Web 界面在线配置，保存后自动重载模型实例，无需重启服务。

### 配置项说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `provider` | 服务商标识 | `openai` |
| `model_name` | 聊天模型名称 | `deepseek-chat` |
| `api_key` | API 密钥 | `sk-xxx` |
| `base_url` | API 地址 | `https://api.deepseek.com/v1` |
| `temperature` | 生成温度（0~2） | `0.5` |
| `max_tokens` | 单次最大生成 token 数 | `4096` |
| `embedding_model` | 向量模型名称 | `BAAI/bge-large-zh-v1.5` |
| `embedding_separate` | 是否独立配置向量模型 | `true` / `false` |
| `embedding_api_key` | 向量模型 API Key（独立时） | `sk-xxx` |
| `embedding_base_url` | 向量模型 API 地址（独立时） | `https://...` |

> 当 `embedding_separate` 为 `false` 时，向量模型复用主模型的 API Key 和 Base URL。
> 模型配置弹窗内置"测试链接"按钮，测试成功后按钮置灰显示"连接成功"，关闭重开可重新测试。

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
| POST | `/api/sessions/{id}/chat` | 发送消息到 Agent（SSE 流式） |
| POST | `/api/sessions/{id}/cancel` | 停止当前会话正在进行的推理 |
| PUT | `/api/sessions/{id}/rename` | 重命名会话 |
| DELETE | `/api/sessions/{id}/delete` | 删除会话 |

### 数据中心

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/data-center/modules` | 采集模块列表及参数定义 |
| POST | `/api/data-center/scrape/stream` | 触发采集（SSE 推送进度） |
| GET | `/api/data-center/jds` | 查询个人/公用 JD |
| GET | `/api/data-center/jds/choices` | 面试可选 JD（个人 + 公用，去重） |
| GET | `/api/data-center/jds/ranking` | 岗位使用排名（个人/公用） |
| GET | `/api/data-center/jds/{id}` | JD 详情 |
| PUT | `/api/data-center/jds/{id}/visibility` | 个人数据 → 公用数据 |
| DELETE | `/api/data-center/jds/{id}` | 删除本人 JD |

### 知识库管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/vector/manual/list` | 列出所有 QA 文档 |
| POST | `/api/vector/manual/add` | 添加 QA 文档 |
| DELETE | `/api/vector/manual/{id}` | 删除 QA 文档 |

### 模型配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config/status` | 查询配置是否就绪 |
| GET | `/api/config/load` | 加载已保存的配置 |
| POST | `/api/config/test` | 测试模型连通性 |
| POST | `/api/config/save` | 保存配置并重载模型 |
| POST | `/api/config/reset` | 重置配置 |

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
A: 检查项目根目录 `.env` 中的 `DB_HOST` / `DB_USER` / `DB_PASSWORD` / `DB_LIBRARY` / `DB_PORT`，确保 MySQL 服务已启动、数据库已创建。

**Q: 提示"AI 模型未配置"？**
A: 首次使用需通过 Web 界面的"模型配置"弹窗完成配置（填写模型名称、API Key、Base URL），保存后即可使用。配置信息存储在 `config.json` 中。

**Q: Agent 初始化失败？**
A: 检查模型配置是否正确，网络是否可访问 API 地址。可通过 `/api/config/status` 接口确认配置状态。

**Q: 语音输入不工作？**
A: Web Speech API 需要 HTTPS 环境或 localhost。确保使用 Chrome/Edge/Safari 最新版，首次使用需授权麦克风权限。

**Q: 知识库为空？**
A: 可通过 Web UI 的"知识库"入口手动添加 QA 条目，也可执行 `python manual/manual_to_vector.py` 初始化内置知识。

**Q: 岗位采集失败或采不到数据？**
A: 检查网络是否可访问招聘网站；Windows 下若虚拟环境路径含中文，libcurl 可能无法加载 CA 证书，程序已自动把证书复制到 ASCII 临时目录规避，如仍失败请查看后端日志中的 `[详情]` / `[错误]` 提示。

**Q: 采集到的岗位 JD 缺少岗位职责？**
A: 详情页抓取受时间预算限制（默认最多 30 条 / 60 秒），超时或详情页无描述时会回退列表页摘要或结构化字段兜底。可重新采集刷新（同一岗位会更新 JD 内容）。

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
