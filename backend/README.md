# Backend — TransAPI Station 后端服务

API 中转站后端，提供用户鉴权、API Key 管理、请求代理与计量、流控、支付充值、管理后台 API。

## 技术栈

- Python 3.12 / FastAPI / Uvicorn
- SQLAlchemy 2.0 (async) + Alembic
- Pydantic v2 + pydantic-settings
- Redis（流控、JWT 黑名单）
- SQLite（开发）/ PostgreSQL（生产）
- httpx（异步转发）
- PyJWT + passlib[bcrypt]

## 快速开始

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8080
```

## 环境变量

见 `.env.example`。

## API 端点

### 认证
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/register` | POST | 用户注册 |
| `/api/v1/auth/login` | POST | 登录获取 JWT |
| `/api/v1/auth/me` | GET | 当前用户信息 |

### API Key
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/keys` | GET | 列出我的 Key |
| `/api/v1/keys` | POST | 创建 Key |
| `/api/v1/keys/{id}` | DELETE | 吊销 Key |
| `/api/v1/keys/{id}` | PATCH | 更新 Key |

### 代理（核心）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/chat/completions` | POST | 聊天补全（转发至上游） |
| `/api/v1/models` | GET | 可用模型列表 |

### 计费
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/billing/usage` | GET | 用量统计 |
| `/api/v1/billing/logs` | GET | 请求日志（分页） |
| `/api/v1/billing/balance` | GET | 余额查询 |
| `/api/v1/billing/recharge` | POST | 兑换码充值 |

### 管理后台（需 admin）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/admin/users` | GET | 用户列表 |
| `/api/v1/admin/users/{id}` | PATCH/DELETE | 编辑/删除用户 |
| `/api/v1/admin/upstream-accounts` | GET/POST | 上游账号管理 |
| `/api/v1/admin/upstream-accounts/sync` | POST | 同步到上游 |
| `/api/v1/admin/recharge-codes` | POST | 生成充值码 |
| `/api/v1/admin/stats` | GET | 系统统计 |

## 请求代理流程

```
Client → Backend(:8080)
  → API Key 鉴权
  → 流控检查（Redis 滑动窗口）
  → 余额预检
  → 选择上游账号
  → httpx 转发至 proxy_web_api
  → Token 计量 + 扣费
  → 返回响应
```

## 目录结构

```
backend/
├── app/
│   ├── main.py           # FastAPI 入口
│   ├── config.py          # 配置
│   ├── database.py        # 数据库引擎
│   ├── models/            # ORM 模型
│   ├── routers/           # API 路由
│   ├── services/          # 业务逻辑
│   ├── middleware/        # 中间件
│   └── utils/             # 工具
├── .env.example
├── requirements.txt
└── Dockerfile
```
