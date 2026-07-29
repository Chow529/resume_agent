# Interview Agent - Web & Terminal

面试模拟 Agent - 支持 Web 界面和终端交互两种方式，集成 RAG（知识库检索）和智联招聘岗位信息抓取。

## 🎯 功能特性

- **智能面试流程**：自动获取用户简历、招聘岗位信息、JD 详情
- **RAG 知识库**：支持 JD 信息的向量化存储与语义检索
- **多平台接入**：提供 Web（FastAPI）和终端（交互式）两种运行方式
- **DESIGN.md 主题**：遵循品牌设计规范的深色 UI 风格

## 📁 项目结构

```
project_root/
├── backend/              ← Web 服务入口
│   ├── __init__.py
│   └── web_app.py        ← FastAPI 主程序
├── frontend/             ← 前端页面
│   └── index.html        ← 面试界面（DESIGN.md 深色主题）
├── agent/                ← Agent 相关
│   ├── __init__.py
│   ├── run_agent.py      ← 终端交互版本
│   └── tools/            ← Agent 工具
│       ├── __init__.py
│       ├── agent_tools.py
│       └── zhaopin_scraper.py
├── rag/                  ← RAG 模块
│   ├── __init__.py
│   ├── ChromaServer.py   ← 向量库管理
│   └── ModelServer.py    ← 模型服务
├── model/                ← 模型配置
│   ├── __init__.py
│   └── MoelFactory.py    ← 模型工厂
├── utils/                ← 工具函数
│   ├── __init__.py
│   ├── logging_tool.py
│   ├── path_tool.py
│   └── readyml_tool.py   ← PDF/YAML 处理
├── prompt/               ← 提示词配置
│   └── prompt.yml
├── .env                  ← 环境变量配置
├── requirements.txt      ← Python 依赖
└── README.md             ← 本文件
```

## 🚀 快速启动

### 1. 安装依赖

```bash
# 创建并激活虚拟环境（Windows）
python -m venv .venv
.\.venv\Scripts\activate

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env_temple` 为 `.env`，并根据实际情况填写 API Key：

```bash
cp .env_temple .env
# 编辑 `.env` 文件，填入 OPENAI_API_KEY 等配置
```

### 3. 准备简历文件

将用户的简历 PDF 放置到项目根目录：

```
job/jobhunter.pdf
```

> 如果 `job/` 目录不存在，请手动创建：`mkdir job`

---

## ▶️ 启动方式

### Web 版（浏览器访问）

```bash
cd backend
uvicorn web_app:app --host 127.0.0.1 --port 8000 --reload
```

访问：[http://127.0.0.1:8000](http://127.0.0.1:8000)

**命令行参数：**

| 参数 | 说明 |
|------|------|
| `--host` | 绑定主机地址（默认 127.0.0.1） |
| `--port` | 端口号（默认 8000） |
| `--reload` | 代码修改后自动重启 |

### 终端版（命令行交互）

```bash
python agent/run_agent.py
```

进入交互式命令行，输入 `/help` 查看可用命令。

---

## 🔗 使用 ngrok 公网访问

如果你希望让其他人可以通过网络访问你的面试 Agent，可以使用 [ngrok](https://ngrok.com/) 将本地服务映射到公网域名。

### 1. 注册并获取 ngrok Authtoken

1. 访问 [ngrok.com](https://ngrok.com/) 注册账号（支持 Google/Facebook/邮箱注册）
2. 登录 Dashboard（[https://ngrok.com/dashboard](https://ngrok.com/dashboard)）
3. 在 **YOUR AUTH TOKEN** 处查看并复制你的 Authtoken

### 2. 下载并安装 ngrok

#### Windows 下载

```bash
# 下载 ngrok（最新版本请前往 ngrok.com 官网获取）
curl -L https://ngrok.s3.amazonaws.com/ngrok-windows-amd64-3.zip -o ngrok.zip
unzip ngrok.zip
```

> ⚠️ 注意：在 PowerShell 或 CMD 中运行，建议将 `ngrok.exe` 加入系统 PATH，或放在项目的 `backend/` 目录下。

#### macOS (使用 Homebrew)

```bash
brew install ngrok
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get install ngrok
```

### 3. 配置 ngrok Authtoken

在终端运行以下命令，将 `<your_authtoken>` 替换为你的实际 Token：

```bash
ngrok config add-authtoken <your_authtoken>
```

**或** 手动编辑 ngrok 配置文件（默认位于 `~/.ngrok2/ngrok.yml`）：

```yaml
authtoken: <your_authtoken>
```

### 4. 启动 ngrok 隧道

有两种启动方式：

**方式 A：快速启动（临时隧道，每次重启失效）**

```bash
cd backend
ngrok http 8000
```

**方式 B：配置持久隧道（建议用于长期使用）**

创建配置文件 `ngrok.yml`（放在 `backend/` 目录或 `~/.ngrok2/`）：

```yaml
tunnels:
  interview-agent:
    proto: http
    addr: 8000
    name: interview-agent
    subdomain: your-subdomain  # 可选，设置自定义子域名
```

然后运行：

```bash
ngrok start -config=ngrok.yml interview-agent
```

### 5. 获取公网访问地址

启动后，ngrok 终端会显示类似以下的输出：

```
ngrok by @dnragot (https://ngrok.com)

Session Status                online
Session Expires               59 minutes, 58 seconds
Version                       3.0.0
Region                        Asia East (shanghai) (CN)
Local                         http://127.0.0.1:8000
Forwarding                    https://abcd-123-45-67-89.ngrok-free.app -> http://127.0.0.1:8000
```

复制 `Forwarding` 中的 HTTPS 地址（如 `https://abcd-123-45-67-89.ngrok-free.app`），分享给他人即可访问面试界面。

### ngrok 常用命令

| 命令 | 说明 |
|------|------|
| `ngrok http 8000` | 快速启动 HTTP 隧道到 8000 端口 |
| `ngrok start -config=ngrok.yml <隧道名>` | 按配置启动持久隧道 |
| `ngrok http --subdomain=myname 8000` | 尝试使用自定义子域名（需付费） |
| `ngrok quit` | 停止 ngrok 服务 |
| `ngrok status` | 查看当前会话状态（如使用 ngrok CLI v3） |

---

## ⚙️ 高级配置

### 自定义端口

```bash
cd backend && uvicorn web_app:app --host 0.0.0.0 --port 8080
```

然后在 ngrok 中使用相同端口：`ngrok http 8080`

### 修改前端样式

编辑 `frontend/index.html` 中的 CSS 变量，可在 `:root` 中修改：

```css
:root {
    --color-canvas: #101010;      /* 画布背景色 */
    --color-primary: #00d992;     /* 主色（绿色） */
    --color-hairline: #3d3a39;    /* 边框色 */
}
```

---

## ❓ 常见问题

**Q: 启动时找不到 PDF 文件**  
A: 请确认简历文件位于 `job/jobhunter.pdf`，目录存在且文件可读。

**Q: Agent 初始化失败**  
A: 检查 `.env` 中的 API Key 是否正确配置，网络是否能访问 OpenAI API。

**Q: 网页样式不显示**  
A: 确保完全刷新页面（Ctrl+F5），检查浏览器控制台是否有 CORS 错误。

**Q: 向量库为空**  
A: 先执行 `/start` 让 Agent 将 JD 信息存入向量库，然后使用 `/vector 关键词` 查询。

**Q: ngrok 连接超时或无法启动**  
A: 检查网络连接，确认已正确配置 Authtoken，或尝试使用 `ngrok http 8000 --region cn` 选择中国节点。

**Q: 想固定 ngrok 公网域名**  
A: ngrok 免费版每次启动都会变化，如需固定域名需要购买付费计划（自定义域名、固定子域名等）。

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE)。