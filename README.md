<div align="center">

# 🚀 TransAPI Station

**将 DeepSeek 网页聊天转化为 OpenAI 兼容 API 的一站式运营平台**

开箱即用的 API 中转站，集成用户管理、计费系统、流控策略、代理池管理，适合个人和团队自建 LLM API 服务。

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## ✨ 特性

| 特性 | 说明 |
|:-----|:-----|
| 🔄 **OpenAI 兼容** | 完全兼容 OpenAI Chat Completions API，可直接替换 `base_url` 使用 |
| 👥 **多用户管理** | 注册/登录、JWT 鉴权、管理员/用户双角色 |
| 💰 **计费系统** | Token 计量扣费、兑换码充值、账单明细查询 |
| 🚦 **流控策略** | 支持 RPM/TPM 限流，防止滥用 |
| 🏊 **代理池管理** | Token 直连 / 账号池双模式，灵活切换上游账号 |
| 📊 **数据看板** | 用户端和管理端独立仪表盘，调用趋势、费用分析一目了然 |
| 🛡️ **反检测** | 上游代理内置 PoW 求解、TLS 指纹伪装 |
| 🐳 **一键部署** | Docker Compose 一键启动全部服务 |

## 📦 支持的模型

| 模型 ID | 说明 |
|:--------|:-----|
| `deepseek-chat` | DeepSeek V3 普通对话 |
| `deepseek-reasoner` | DeepSeek R1 深度思考 |
| `deepseek-chat-search` | V3 + 联网搜索 |
| `deepseek-reasoner-search` | R1 + 联网搜索 |

## 🏗️ 系统架构

```
                          ┌─────────────────────────────────────────────┐
                          │           TransAPI Station                  │
┌──────────┐  HTTP  ┌─────┴──────┐  HTTP  ┌──────────────┐             │
│  客户端   │───────▶│  前端 SPA   │───────▶│  后端 API     │             │
│ 浏览器/  │        │  React     │        │  FastAPI     │             │
│ API 调用  │        │  :80       │        │  :8080       │             │
└──────────┘        └────────────┘        └──────┬───────┘             │
                                                 │                     │
                                    ┌────────────┼────────────┐        │
                                    │            │            │        │
                              ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐  │
                              │  上游代理   │ │ Redis │ │  SQLite/  │  │
                              │  DeepSeek  │ │ :6379 │ │ PostgreSQL│  │
                              │  :8000     │ │       │ │           │  │
                              └───────────┘ └───────┘ └───────────┘  │
                          └─────────────────────────────────────────────┘
```

**请求流程**：客户端 → 鉴权 + 流控 + 余额预检 → 上游代理 (PoW 求解 + 反检测) → OpenAI 格式响应 → Token 计量 + 扣费 + 日志

## 🚀 快速开始

### 环境要求

- Docker 20.10+ & Docker Compose v2
- 或手动部署：Python 3.12+ / Node.js 18+

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/honey1000001001/transapi_station.git
cd transapi_station

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少修改 JWT_SECRET、REDIS_PASSWORD、ADMIN_PASSWORD

# 3. 配置上游代理
cp proxy_web_api/config.json.example proxy_web_api/config.json
# 编辑 config.json，填入 DeepSeek 账号信息

# 4. 启动全部服务
docker compose up -d
```

启动后访问：

| 服务 | 地址 |
|:-----|:-----|
| 用户界面 | http://localhost |
| 后端 API | http://localhost:8080 |
| 上游代理 | http://localhost:2063 |

> 默认管理员：`admin@transapi.local` / `changeme`

### 方式二：开发模式

```bash
# 后端
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8080

# 前端（另一个终端）
cd frontend
npm install
npm run dev
```

## 💡 API 接入

TransAPI Station 完全兼容 OpenAI API 格式，只需修改 `base_url` 即可无缝接入。

### curl

```bash
curl http://localhost/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'
```

### Python（OpenAI SDK）

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="http://localhost/api/v1"
)

resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "你好"}],
    stream=True
)
for chunk in resp:
    print(chunk.choices[0].delta.content or "", end="")
```

### Node.js

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "YOUR_API_KEY",
  baseURL: "http://localhost/api/v1",
});

const stream = await client.chat.completions.create({
  model: "deepseek-chat",
  messages: [{ role: "user", content: "你好" }],
  stream: true,
});

for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content || "");
}
```

## ⚙️ 环境变量

| 变量 | 说明 | 默认值 |
|:-----|:-----|:-------|
| `JWT_SECRET` | JWT 签名密钥（⚠️ 生产必须修改） | `change-me-in-production` |
| `REDIS_PASSWORD` | Redis 密码 | `changeme` |
| `ADMIN_EMAIL` | 默认管理员邮箱 | `admin@transapi.local` |
| `ADMIN_PASSWORD` | 默认管理员密码 | `changeme` |
| `UPSTREAM_API_KEY` | 上游代理 API Key | - |
| `FRONTEND_PORT` | 前端端口 | `80` |
| `BACKEND_PORT` | 后端端口 | `8080` |
| `PROXY_PORT` | 上游代理端口 | `2063` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `CORS_ORIGINS` | CORS 允许的来源（逗号分隔） | `http://localhost` |
| `DEBUG` | 调试模式 | `false` |

> 完整配置见 [`.env.example`](.env.example)

## 🛠️ 技术栈

```
前端    React 18 · TypeScript · Arco Design · Vite 5 · Zustand · Recharts
后端    Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Pydantic v2 · httpx · PyJWT
缓存    Redis 7（流控计数器 · JWT 黑名单）
数据库  SQLite（开发）/ PostgreSQL（生产）
代理    FastAPI · curl_cffi · wasmtime（PoW 求解 · TLS 指纹伪装）
部署    Docker Compose · Nginx
```

## 📁 项目结构

```
transapi_station/
├── backend/                  # 后端 API 服务
│   └── app/
│       ├── models/           # SQLAlchemy 数据模型
│       ├── routers/          # API 路由（auth / admin / proxy / billing）
│       ├── services/         # 业务逻辑层
│       ├── middleware/       # 鉴权中间件
│       └── utils/            # 工具函数
├── frontend/                 # 前端 React SPA
│   └── src/
│       ├── pages/            # 页面（用户端 + 管理端）
│       ├── components/       # 公共组件
│       ├── api/              # API 请求封装
│       ├── hooks/            # 自定义 Hooks
│       └── stores/           # Zustand 状态管理
├── proxy_web_api/            # 上游 DeepSeek 代理
│   └── app.py                # 核心代理逻辑（PoW · 反检测）
├── docker-compose.yml        # Docker 编排
└── .env.example              # 环境变量模板
```

## 🤝 参与贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的特性分支：`git checkout -b feature/amazing-feature`
3. 提交你的更改：`git commit -m 'feat: add amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

## 📄 许可证

本项目基于 [Apache License 2.0](LICENSE) 开源。

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

</div>
