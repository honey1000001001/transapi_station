# proxy_web_api — DeepSeek Web Chat 代理

将 DeepSeek 网页免费聊天转换为 OpenAI 兼容 API 的反向代理服务。

## 特性

- 完全兼容 OpenAI API 格式（流式/非流式）
- 支持 deepseek-chat / deepseek-reasoner(R1) / 联网搜索变体
- 双认证模式：账号池轮询 / 浏览器 Token 直连
- 自动处理 DeepSeek PoW 挑战（WASM sha3）
- 反检测：伪造浏览器指纹、Cookie、遥测事件上报、TLS 指纹伪装

## 快速开始

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config.json.example config.json
# 编辑 config.json 填入账号信息
python3 app.py  # 默认端口 8000
```

## 配置

编辑 `config.json`：

```json
{
  "api_key": "sk-deepseek2api",
  "accounts": [
    {"email": "user@example.com", "password": "xxx", "token": ""}
  ]
}
```

- `api_key`：调用时的 Bearer Token（账号池模式）
- `accounts`：DeepSeek 账号列表，服务自动轮询登录获取 token

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/chat/completions` | POST | 聊天补全（OpenAI 兼容） |
| `/v1/models` | GET | 可用模型列表 |
| `/health` | GET | 健康检查 |
| `/admin/login` | POST | 手动登录账号获取 token |
| `/admin/accounts` | GET | 账号池状态 |
| `/admin/accounts` | PUT | 更新账号列表（由后端同步调用） |

## 认证模式

**直连模式**：客户端 Bearer Token 直接作为 DeepSeek token 使用

**账号池模式**：客户端 Bearer Token 匹配 `api_key`，服务从 accounts 轮询选择账号并自动登录

## 可用模型

| 模型 ID | 说明 |
|---------|------|
| `deepseek-chat` | V3 普通对话 |
| `deepseek-reasoner` | R1 深度思考 |
| `deepseek-chat-search` | V3 + 联网搜索 |
| `deepseek-reasoner-search` | R1 + 联网搜索 |

## 注意事项

- 浏览器 Token 会过期，直连模式需定期刷新
- 账号池模式下服务自动登录刷新 token
- 高频调用有封号风险
