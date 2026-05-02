# TransAPI Station — API 中转站

> 将 DeepSeek 网页聊天转化为 OpenAI 兼容 API 服务，提供用户管理、计费、流控、代理池等完整运营能力。

---

## 系统架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   用户/客户端  │────▶│  前端 (Nginx) │────▶│  后端 (FastAPI)│────▶│  上游代理     │
│  浏览器/API   │     │  :80         │     │  :8080       │     │  :8000       │
│              │     │  React SPA   │     │  鉴权/计费/流控│     │  DeepSeek→API│
└──────────────┘     └──────────────┘     └──────┬───────┘     └──────────────┘
                                                  │
                                            ┌─────▼─────┐
                                            │   Redis    │
                                            │   :6379    │
                                            │  流控/缓存  │
                                            └───────────┘
```

**请求流**：客户端 → 后端鉴权 + 流控检查 + 余额预检 → 转发至上游代理 → 处理 DeepSeek PoW 和反检测 → 返回 OpenAI 格式响应 → Token 计量 + 扣费 + 记日志

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourname/transapi_station.git
cd transapi_station
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，至少修改 JWT_SECRET 和 REDIS_PASSWORD
```

### 3. 配置上游代理

```bash
cp proxy_web_api/config.json.example proxy_web_api/config.json
# 编辑 config.json，填入 DeepSeek 账号信息
```

### 4. 启动服务

```bash
docker compose up -d
```

服务启动后访问：
- **用户界面**：http://localhost
- **管理后台**：http://localhost（admin 账号登录后自动跳转）
- **后端 API**：http://localhost:8080
- **上游代理**：http://localhost:2063

默认管理员：`admin@transapi.local` / `changeme`

### 5. 开发模式

```bash
# 后端
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8080

# 前端
cd frontend && npm install && npm run dev
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18, TypeScript, Arco Design (字节风格 UI), Vite 5, React Router v6, Axios, Recharts |
| 后端 | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, httpx, PyJWT |
| 缓存 | Redis 7（流控计数器、JWT 黑名单） |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| 上游代理 | FastAPI + curl_cffi + wasmtime（PoW 求解 + 反检测 + TLS 指纹伪装） |
| 部署 | Docker Compose, Nginx |

---

## 支持的模型

| 模型 ID | 说明 |
|---------|------|
| `deepseek-chat` | DeepSeek V3 普通对话 |
| `deepseek-reasoner` | DeepSeek R1 深度思考 |
| `deepseek-chat-search` | V3 + 联网搜索 |
| `deepseek-reasoner-search` | R1 + 联网搜索 |

---

## 功能概览

### 用户端

| 功能 | 说明 |
|------|------|
| 注册/登录 | 邮箱注册，JWT 鉴权 |
| 仪表盘 | 余额、调用次数、Token 消耗、费用趋势 |
| API Key 管理 | 创建/吊销 Key，RPM/TPM 限额 |
| 充值 | 兑换码充值 |
| 账单明细 | 请求日志、费用汇总 |
| 接入文档 | 快速开始指南、价格说明、代码示例 |

### 管理后台

| 功能 | 说明 |
|------|------|
| 管理仪表盘 | 总览统计、趋势图 |
| 用户管理 | 搜索/编辑/禁用用户、调整余额 |
| 流控配置 | RPM/TPM 限额设置 |
| 代理池管理 | 上游账号管理、Token 直连/账号池双模式 |
| 充值码管理 | 批量生成、查看状态 |
| 系统统计 | 收入趋势、模型分布、错误率 |

---

## API 接入示例

### curl

```bash
curl http://localhost/api/v1/chat/completions \
  -H "Authorization: Bearer sk-your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"你好"}],"stream":true}'
```

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-api-key",
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

---

## 环境变量

见 `.env.example`。关键变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JWT_SECRET` | JWT 签名密钥（生产必须修改） | `change-me-in-production` |
| `REDIS_PASSWORD` | Redis 密码 | `changeme` |
| `ADMIN_EMAIL` | 默认管理员邮箱 | `admin@transapi.local` |
| `ADMIN_PASSWORD` | 默认管理员密码 | `changeme` |
| `UPSTREAM_API_KEY` | 上游代理 API Key | `sk-deepseek2api` |

---

## 目录结构

```
transapi_station/
├── backend/                # 后端 FastAPI 服务
│   ├── app/
│   │   ├── models/         # 数据库模型
│   │   ├── routers/        # API 路由
│   │   ├── services/       # 业务逻辑
│   │   ├── middleware/     # 中间件
│   │   └── utils/          # 工具函数
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # 前端 React 应用
│   ├── src/
│   │   ├── api/            # API 请求封装
│   │   ├── pages/          # 页面组件
│   │   ├── components/     # 公共组件
│   │   └── stores/         # 状态管理
│   ├── Dockerfile
│   └── nginx.conf
├── proxy_web_api/          # 上游 DeepSeek 代理
│   ├── app.py              # 核心代理逻辑
│   └── Dockerfile
├── docker-compose.yml      # Docker 部署编排
├── .env.example            # 环境变量模板
└── README.md
```

---

## License

MIT
