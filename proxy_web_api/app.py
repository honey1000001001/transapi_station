"""
DeepSeek Web Chat -> OpenAI Compatible API Server

将 DeepSeek 网页免费聊天转换为 OpenAI 兼容的 API 服务

支持的端点:
  GET  /v1/models             - 列出可用模型
  POST /v1/chat/completions   - 聊天补全（流式/非流式）
  GET  /                      - 欢迎页面
  GET  /health                - 健康检查
  POST /admin/accounts        - 管理账号
  POST /admin/login           - 登录账号获取 token

认证方式:
  - 配置模式: 请求头 Bearer token 匹配 config.json 中的 api_key，使用配置中的账号轮询
  - 直连模式: 请求头 Bearer token 直接作为 DeepSeek 的认证 token（从浏览器提取）
"""

import base64
import ctypes
import json
import logging
import os
import queue
import random
import re
import struct
import threading
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from curl_cffi import requests as curl_requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from wasmtime import Linker, Module, Store

# ======================== 日志配置 ========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("deepseek2api")

# ======================== 配置管理 ========================
CONFIG_PATH = "config.json"


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[load_config] 无法读取配置文件: {e}")
        return {}


def save_config(cfg: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[save_config] 写入配置文件失败: {e}")


CONFIG = load_config()

# ======================== 账号队列管理 ========================
account_queue = []
queue_lock = threading.Lock()


def init_account_queue():
    global account_queue
    with queue_lock:
        account_queue = CONFIG.get("accounts", [])[:]
        random.shuffle(account_queue)


init_account_queue()


def get_account_id(account: dict) -> str:
    return account.get("email", "").strip() or account.get("mobile", "").strip()


def choose_account(exclude_ids: list = None) -> Optional[dict]:
    if exclude_ids is None:
        exclude_ids = []
    with queue_lock:
        for i in range(len(account_queue)):
            acc = account_queue[i]
            acc_id = get_account_id(acc)
            if acc_id and acc_id not in exclude_ids:
                logger.info(f"[choose_account] 选择账号: {acc_id}")
                return account_queue.pop(i)
    logger.warning("[choose_account] 没有可用账号")
    return None


def release_account(account: dict):
    with queue_lock:
        account_queue.append(account)


# ======================== DeepSeek 常量 ========================
DEEPSEEK_HOST = "chat.deepseek.com"
DEEPSEEK_LOGIN_URL = f"https://{DEEPSEEK_HOST}/api/v0/users/login"
DEEPSEEK_CREATE_SESSION_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat_session/create"
DEEPSEEK_CREATE_POW_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat/create_pow_challenge"
DEEPSEEK_COMPLETION_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat/completion"
DEEPSEEK_DELETE_SESSION_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat_session/delete"
DEEPSEEK_EVENTS_URL = f"https://{DEEPSEEK_HOST}/api/v0/events"

# 当前 IP 缓存
_cached_ip = ""
_ip_lock = threading.Lock()

BASE_HEADERS = {
    "Host": "chat.deepseek.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Content-Type": "application/json",
    "Origin": "https://chat.deepseek.com",
    "Referer": "https://chat.deepseek.com/",
    "Sec-Ch-Ua": '"Microsoft Edge";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "x-app-version": "20241129.1",
    "x-client-locale": "zh_CN",
    "x-client-platform": "web",
    "x-client-timezone-offset": "28800",
    "x-client-version": "1.8.0",
}

# Cookie 生成 - 模拟真实浏览器 session
def generate_cookie() -> str:
    """生成伪造的 DeepSeek 浏览器 Cookie"""
    ts = int(time.time())
    hex_id = os.urandom(9).hex()
    uuid1 = str(uuid.uuid4())
    uuid2 = str(uuid.uuid4())
    uuid3 = str(uuid.uuid4())
    return (
        f"intercom-HWWAFSESTIME={ts}; "
        f"HWWAFSESID={hex_id}; "
        f"Hm_lvt_{uuid1}={ts},{ts},{ts}; "
        f"Hm_lpvt_{uuid2}={ts}; "
        f"_frid={uuid3}; "
        f"_fr_ssid={str(uuid.uuid4())}; "
        f"_fr_pvid={str(uuid.uuid4())}"
    )

# x-hif 指纹头生成 - DeepSeek 服务端校验格式但不验证签名
def generate_hif_token() -> str:
    """生成 AWS WAF 指纹格式的 token: base64(41bytes).base64(12bytes)"""
    sig = base64.b64encode(os.urandom(41)).decode().rstrip("=")[:56]
    nonce = base64.b64encode(os.urandom(12)).decode().rstrip("=")[:16]
    return f"{sig}.{nonce}"

# WASM 模块路径
WASM_PATH = "sha3_wasm_bg.7b9ca65ddd.wasm"

# 模型配置
MODEL_CONFIG = {
    "deepseek-chat": {"thinking": False, "search": False},
    "deepseek-v3": {"thinking": False, "search": False},
    "deepseek-reasoner": {"thinking": True, "search": False},
    "deepseek-r1": {"thinking": True, "search": False},
    "deepseek-chat-search": {"thinking": False, "search": True},
    "deepseek-v3-search": {"thinking": False, "search": True},
    "deepseek-reasoner-search": {"thinking": True, "search": True},
    "deepseek-r1-search": {"thinking": True, "search": True},
}

# Keep-alive 超时（秒）
KEEP_ALIVE_TIMEOUT = 5


# ======================== 登录函数 ========================
def login_deepseek(account: dict) -> str:
    """使用 email/mobile + password 登录 DeepSeek，返回 token"""
    email = account.get("email", "").strip()
    mobile = account.get("mobile", "").strip()
    password = account.get("password", "").strip()

    if not password or (not email and not mobile):
        raise ValueError("账号缺少必要的登录信息")

    if email:
        payload = {"email": email, "password": password, "device_id": "deepseek_to_api", "os": "android"}
    else:
        payload = {"mobile": mobile, "area_code": None, "password": password, "device_id": "deepseek_to_api", "os": "android"}

    try:
        resp = curl_requests.post(DEEPSEEK_LOGIN_URL, headers=BASE_HEADERS, json=payload, impersonate="chrome131")
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"[login_deepseek] 登录请求异常: {e}")
        raise ValueError(f"登录请求异常: {e}")

    if not data.get("data", {}).get("biz_data", {}).get("user", {}):
        logger.error(f"[login_deepseek] 登录响应格式错误: {data}")
        raise ValueError("登录响应格式错误")

    token = data["data"]["biz_data"]["user"].get("token")
    if not token:
        raise ValueError("登录响应中缺少 token")

    account["token"] = token
    save_config(CONFIG)
    logger.info(f"[login_deepseek] 账号 {get_account_id(account)} 登录成功")
    return token


# ======================== 认证中间件 ========================
def authenticate(request: Request):
    """
    判断认证模式:
    - 配置模式: Bearer token 匹配 config 中的 api_key，使用账号池
    - 直连模式: Bearer token 直接作为 DeepSeek token
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少 Bearer token 认证")

    caller_key = auth_header.replace("Bearer ", "", 1).strip()
    config_key = CONFIG.get("api_key", "")

    if config_key and caller_key == config_key:
        # 配置模式 - 从账号池选择
        request.state.use_config_token = True
        request.state.tried_accounts = []
        account = choose_account()
        if not account:
            raise HTTPException(status_code=429, detail="没有可用账号或所有账号都在使用中")

        if not account.get("token", "").strip():
            try:
                login_deepseek(account)
            except Exception as e:
                release_account(account)
                raise HTTPException(status_code=500, detail=f"账号登录失败: {e}")

        request.state.deepseek_token = account.get("token")
        request.state.account = account
    else:
        # 直连模式 - 直接使用用户提供的 token
        request.state.use_config_token = False
        request.state.deepseek_token = caller_key
        request.state.account = None


def get_auth_headers(request: Request) -> dict:
    """构造带认证和反检测头的请求头"""
    return {
        **BASE_HEADERS,
        "authorization": f"Bearer {request.state.deepseek_token}",
        "x-hif-dliq": generate_hif_token(),
        "x-hif-leim": generate_hif_token(),
        "Cookie": generate_cookie(),
    }


# ======================== PoW 计算器 ========================
def compute_pow_answer(algorithm: str, challenge_str: str, salt: str,
                       difficulty: int, expire_at: int, wasm_path: str) -> Optional[int]:
    """使用 WASM 模块计算 Proof-of-Work 答案"""
    if algorithm != "DeepSeekHashV1":
        raise ValueError(f"不支持的算法: {algorithm}")

    prefix = f"{salt}_{expire_at}_"

    # 加载并实例化 WASM 模块
    store = Store()
    linker = Linker(store.engine)

    with open(wasm_path, "rb") as f:
        wasm_bytes = f.read()
    module = Module(store.engine, wasm_bytes)
    instance = linker.instantiate(store, module)
    exports = instance.exports(store)

    memory = exports["memory"]
    add_to_stack = exports["__wbindgen_add_to_stack_pointer"]
    alloc = exports["__wbindgen_export_0"]
    wasm_solve = exports["wasm_solve"]

    def write_memory(offset: int, data: bytes):
        base_addr = ctypes.cast(memory.data_ptr(store), ctypes.c_void_p).value
        ctypes.memmove(base_addr + offset, data, len(data))

    def read_memory(offset: int, size: int) -> bytes:
        base_addr = ctypes.cast(memory.data_ptr(store), ctypes.c_void_p).value
        return ctypes.string_at(base_addr + offset, size)

    def encode_string(text: str):
        data = text.encode("utf-8")
        ptr_val = alloc(store, len(data), 1)
        ptr = int(ptr_val.value) if hasattr(ptr_val, "value") else int(ptr_val)
        write_memory(ptr, data)
        return ptr, len(data)

    # 申请栈空间
    retptr = add_to_stack(store, -16)
    # 编码 challenge 和 prefix
    ptr_challenge, len_challenge = encode_string(challenge_str)
    ptr_prefix, len_prefix = encode_string(prefix)
    # 调用 wasm_solve
    wasm_solve(store, retptr, ptr_challenge, len_challenge, ptr_prefix, len_prefix, float(difficulty))
    # 读取结果
    status_bytes = read_memory(retptr, 4)
    status = struct.unpack("<i", status_bytes)[0] if len(status_bytes) == 4 else 0
    value_bytes = read_memory(retptr + 8, 8)
    value = struct.unpack("<d", value_bytes)[0] if len(value_bytes) == 8 else 0
    # 恢复栈
    add_to_stack(store, 16)

    return int(value) if status != 0 else None


def get_pow_response(token: str, max_attempts: int = 3) -> Optional[str]:
    """获取 PoW 挑战并计算答案，返回 base64 编码的 PoW 响应"""
    headers = {
        **BASE_HEADERS,
        "authorization": f"Bearer {token}",
        "x-hif-dliq": generate_hif_token(),
        "x-hif-leim": generate_hif_token(),
        "Cookie": generate_cookie(),
    }

    for attempt in range(max_attempts):
        try:
            resp = curl_requests.post(
                DEEPSEEK_CREATE_POW_URL,
                headers=headers,
                json={"target_path": "/api/v0/chat/completion"},
                timeout=30,
                impersonate="chrome131",
            )
            data = resp.json()
        except Exception as e:
            logger.error(f"[get_pow_response] 请求异常: {e}")
            continue

        if resp.status_code == 200 and data.get("code") == 0:
            challenge = data["data"]["biz_data"]["challenge"]
            try:
                answer = compute_pow_answer(
                    challenge["algorithm"],
                    challenge["challenge"],
                    challenge["salt"],
                    challenge.get("difficulty", 144000),
                    challenge.get("expire_at", 0),
                    WASM_PATH,
                )
            except Exception as e:
                logger.error(f"[get_pow_response] PoW 计算异常: {e}")
                answer = None

            if answer is None:
                logger.warning("[get_pow_response] PoW 答案计算失败，重试中...")
                continue

            pow_dict = {
                "algorithm": challenge["algorithm"],
                "challenge": challenge["challenge"],
                "salt": challenge["salt"],
                "answer": answer,
                "signature": challenge["signature"],
                "target_path": challenge["target_path"],
            }
            pow_str = json.dumps(pow_dict, separators=(",", ":"), ensure_ascii=False)
            return base64.b64encode(pow_str.encode("utf-8")).decode("utf-8")
        else:
            logger.warning(f"[get_pow_response] 获取 PoW 失败: code={data.get('code')}, msg={data.get('msg')}")
            continue

    return None


# ======================== 会话管理 ========================
def create_session(token: str, max_attempts: int = 3) -> Optional[str]:
    """创建聊天会话，返回 session_id"""
    headers = {
        **BASE_HEADERS,
        "authorization": f"Bearer {token}",
        "x-hif-dliq": generate_hif_token(),
        "x-hif-leim": generate_hif_token(),
        "Cookie": generate_cookie(),
    }

    for attempt in range(max_attempts):
        try:
            resp = curl_requests.post(
                DEEPSEEK_CREATE_SESSION_URL,
                headers=headers,
                json={"agent": "chat"},
                impersonate="chrome131",
            )
            data = resp.json()
        except Exception as e:
            logger.error(f"[create_session] 请求异常: {e}")
            continue

        if resp.status_code == 200 and data.get("code") == 0:
            # 兼容新旧 API 响应: 新版 biz_data.chat_session.id / 旧版 biz_data.id
            biz_data = data["data"]["biz_data"]
            if "chat_session" in biz_data:
                session_id = biz_data["chat_session"]["id"]
            else:
                session_id = biz_data["id"]
            logger.info(f"[create_session] 创建会话成功: {session_id}")
            return session_id
        else:
            logger.warning(f"[create_session] 创建会话失败: code={data.get('code')}, msg={data.get('msg')}")
            continue

    return None


def delete_session(token: str, session_id: str):
    """删除聊天会话"""
    headers = {
        **BASE_HEADERS,
        "authorization": f"Bearer {token}",
        "x-hif-dliq": generate_hif_token(),
        "x-hif-leim": generate_hif_token(),
        "Cookie": generate_cookie(),
    }
    try:
        resp = curl_requests.post(
            DEEPSEEK_DELETE_SESSION_URL,
            headers=headers,
            json={"chat_session_id": session_id},
            impersonate="chrome131",
            timeout=3,
        )
        if resp.status_code == 200:
            logger.info(f"[delete_session] 删除会话成功: {session_id}")
        else:
            logger.warning(f"[delete_session] 删除会话失败: {resp.status_code}")
    except Exception as e:
        logger.warning(f"[delete_session] 请求异常: {e}")


# ======================== 遥测事件上报（防封号） ========================
EVENT_COMMIT_ID = "41e9c7b1"


def get_ip_address() -> str:
    """获取当前出口 IP 地址（缓存）"""
    global _cached_ip
    with _ip_lock:
        if _cached_ip:
            return _cached_ip
    try:
        resp = curl_requests.get(
            "https://chat.deepseek.com/",
            headers={**BASE_HEADERS, "Cookie": generate_cookie()},
            impersonate="chrome131",
            timeout=15,
        )
        match = re.search(r'<meta name="ip" content="([\d.]+)">', resp.text)
        if match:
            _cached_ip = match.group(1)
            logger.info(f"[get_ip_address] 当前 IP: {_cached_ip}")
            return _cached_ip
    except Exception as e:
        logger.warning(f"[get_ip_address] 获取 IP 失败: {e}")
    return "0.0.0.0"


def _make_event(session_id: str, ts: int, name: str, message: str, payload: dict, level: str = "info") -> dict:
    """构造单个遥测事件"""
    return {
        "session_id": session_id,
        "client_timestamp_ms": ts,
        "event_name": name,
        "event_message": message,
        "payload": {
            "__location": "https://chat.deepseek.com/",
            "__ip": get_ip_address(),
            "__region": "CN",
            "__pageVisibility": "true",
            "__nodeEnv": "production",
            "__deployEnv": "production",
            "__appVersion": BASE_HEADERS["x-app-version"],
            "__commitId": EVENT_COMMIT_ID,
            "__userAgent": BASE_HEADERS["User-Agent"],
            "__referrer": "",
            **payload,
        },
        "level": level,
    }


def send_events(session_id: str, token: str, thinking_enabled: bool = False):
    """在后台线程发送模拟遥测事件，缓解封号风险"""
    try:
        session_event_id = f"session_v0_{uuid.uuid4().hex[:16]}"
        ts = int(time.time() * 1000)
        ip = get_ip_address()

        events = [
            _make_event(session_event_id, ts, "__reportEvent", "调用上报事件接口",
                        {"method": "post", "url": "/api/v0/events", "path": "/api/v0/events"}),
            _make_event(session_event_id, ts + 100 + random.randint(0, 1000), "__reportEventOk", "调用上报事件接口成功",
                        {"method": "post", "url": "/api/v0/events", "path": "/api/v0/events",
                         "logId": str(uuid.uuid4()), "metricDuration": random.randint(100, 900), "status": "200"}),
            _make_event(session_event_id, ts + 200 + random.randint(0, 1000), "createSessionAndStartCompletion", "开始创建对话",
                        {"agentId": "chat", "thinkingEnabled": str(thinking_enabled).lower()}),
            _make_event(session_event_id, ts + 300 + random.randint(0, 1000), "__httpRequest",
                        "httpRequest POST /api/v0/chat_session/create",
                        {"url": "/api/v0/chat_session/create", "path": "/api/v0/chat_session/create", "method": "POST"}),
            _make_event(session_event_id, ts + 400 + random.randint(0, 1000), "__httpResponse",
                        f"httpResponse POST /api/v0/chat_session/create, {random.randint(100, 800)}ms, reason: none",
                        {"url": "/api/v0/chat_session/create", "path": "/api/v0/chat_session/create", "method": "POST",
                         "metricDuration": random.randint(100, 800), "status": "200", "logId": str(uuid.uuid4())}),
            _make_event(session_event_id, ts + 600 + random.randint(0, 1000), "chatCompletionApi", "chatCompletionApi 被调用",
                        {"scene": "completion", "chatSessionId": session_id,
                         "withFile": "false", "thinkingEnabled": str(thinking_enabled).lower()}),
            _make_event(session_event_id, ts + 700 + random.randint(0, 1000), "__httpRequest",
                        "httpRequest POST /api/v0/chat/completion",
                        {"url": "/api/v0/chat/completion", "path": "/api/v0/chat/completion", "method": "POST"}),
            _make_event(session_event_id, ts + 800 + random.randint(0, 1000), "completionFirstChunkReceived",
                        "收到第一个 completion chunk",
                        {"metricDuration": random.randint(200, 2000), "logId": str(uuid.uuid4())}),
            _make_event(session_event_id, ts + 1000 + random.randint(0, 1000), "routeChange",
                        f"路由改变 => /a/chat/s/{session_id}",
                        {"to": f"/a/chat/s/{session_id}", "redirect": "false", "redirected": "false",
                         "redirectReason": "", "redirectTo": "/", "hasToken": "true", "hasUserInfo": "true"}),
            _make_event(session_event_id, ts + 1200 + random.randint(0, 1000), "__httpResponse",
                        f"httpResponse POST /api/v0/chat/completion, {random.randint(500, 5000)}ms, reason: none",
                        {"url": "/api/v0/chat/completion", "path": "/api/v0/chat/completion", "method": "POST",
                         "metricDuration": random.randint(500, 5000), "status": "200", "logId": str(uuid.uuid4())}),
            _make_event(session_event_id, ts + 1400 + random.randint(0, 1000), "completionApiOk",
                        "完成响应，响应有正常的 finish reason",
                        {"condition": "hasDone", "streamClosed": False, "scene": "completion", "chatSessionId": session_id}),
        ]

        headers = {
            **BASE_HEADERS,
            "authorization": f"Bearer {token}",
            "Referer": f"https://chat.deepseek.com/a/chat/s/{session_id}",
            "x-hif-dliq": generate_hif_token(),
            "x-hif-leim": generate_hif_token(),
            "Cookie": generate_cookie(),
        }

        resp = curl_requests.post(
            DEEPSEEK_EVENTS_URL,
            headers=headers,
            json={"events": events},
            impersonate="chrome131",
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info(f"[send_events] 遥测事件上报成功 session={session_id}")
        else:
            logger.warning(f"[send_events] 上报失败: {resp.status_code}")
    except Exception as e:
        logger.warning(f"[send_events] 上报异常: {e}")


# ======================== 消息预处理 ========================
def messages_prepare(messages: list) -> str:
    """
    将 OpenAI 格式的 messages 数组转换为 DeepSeek 网页端的 prompt 格式
    - 合并连续相同角色的消息
    - 为 assistant 消息添加 <｜Assistant｜> 前缀和 <｜end▁of▁sentence｜> 后缀
    - 为非首条 user/system 消息添加 <｜User｜> 前缀
    """
    processed = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        if isinstance(content, list):
            texts = [item.get("text", "") for item in content if item.get("type") == "text"]
            text = "\n".join(texts)
        else:
            text = str(content)
        processed.append({"role": role, "text": text})

    if not processed:
        return ""

    # 合并连续同角色消息
    merged = [processed[0]]
    for msg in processed[1:]:
        if msg["role"] == merged[-1]["role"]:
            merged[-1]["text"] += "\n\n" + msg["text"]
        else:
            merged.append(msg)

    # 添加标签
    parts = []
    for idx, block in enumerate(merged):
        role = block["role"]
        text = block["text"]
        if role == "assistant":
            parts.append(f"<｜Assistant｜>{text}<｜end▁of▁sentence｜>")
        elif role in ("user", "system"):
            if idx > 0:
                parts.append(f"<｜User｜>{text}")
            else:
                parts.append(text)
        else:
            parts.append(text)

    return "".join(parts)


# ======================== 补全请求 ========================
def call_completion(payload: dict, headers: dict, max_attempts: int = 3):
    """调用 DeepSeek 补全接口，返回流式响应"""
    for attempt in range(max_attempts):
        try:
            resp = curl_requests.post(
                DEEPSEEK_COMPLETION_URL,
                headers=headers,
                json=payload,
                stream=True,
                impersonate="chrome131",
            )
            if resp.status_code == 200:
                return resp
            else:
                logger.warning(f"[call_completion] 状态码: {resp.status_code}")
                resp.close()
        except Exception as e:
            logger.warning(f"[call_completion] 请求异常: {e}")
        time.sleep(1)
    return None


# ======================== SSE 流式响应解析 ========================
def parse_deepseek_stream(deepseek_resp, result_queue: queue.Queue, thinking_enabled: bool, search_enabled: bool):
    """在后台线程中解析 DeepSeek 的 SSE 流，将解析后的 chunk 放入队列
    兼容旧版(v=string, p=response/content)和新版(v=response对象, fragments结构)
    """
    ptype = "text"
    try:
        for raw_line in deepseek_resp.iter_lines():
            try:
                line = raw_line.decode("utf-8")
            except Exception:
                continue

            if not line or line.startswith("event:"):
                # 跳过空行和 event: 行 (ready, update_session, title, close 等)
                # 但 event: close 表示流结束
                if line.strip() == "event: close":
                    result_queue.put(None)
                    break
                continue

            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    result_queue.put(None)
                    break

                try:
                    chunk = json.loads(data_str)

                    # ---- 新版 API 格式: v 是 response 对象 ----
                    if isinstance(chunk.get("v"), dict) and "response" in chunk["v"]:
                        response_obj = chunk["v"]["response"]
                        # 从 fragments 提取内容
                        fragments = response_obj.get("fragments", [])
                        for frag in fragments:
                            frag_type = frag.get("type", "")
                            frag_content = frag.get("content", "")

                            if not frag_content:
                                continue

                            if frag_type == "THINKING":
                                if thinking_enabled:
                                    result_queue.put({"type": "thinking", "content": frag_content})
                            elif frag_type == "RESPONSE":
                                # 去除 citation 标签
                                if search_enabled and frag_content.startswith("[citation:"):
                                    continue
                                result_queue.put({"type": "text", "content": frag_content})
                            elif frag_type == "SEARCH":
                                # 搜索结果，跳过
                                continue

                        # 检查状态
                        status = response_obj.get("status", "")
                        if status == "FINISHED" or status == "COMPLETE":
                            result_queue.put(None)
                            break
                        continue

                    # ---- 新版 API 格式: v 是数组(状态变更) ----
                    if isinstance(chunk.get("v"), list):
                        for item in chunk["v"]:
                            if item.get("p") == "quasi_status" and item.get("v") == "FINISHED":
                                result_queue.put(None)
                                return
                        continue

                    # ---- 旧版 API 格式 ----
                    if "v" not in chunk:
                        continue

                    v_value = chunk["v"]

                    # 状态检查
                    if chunk.get("p") == "response/status":
                        if v_value == "FINISHED":
                            result_queue.put(None)
                            break
                        continue

                    if chunk.get("p") == "response/search_status":
                        continue

                    # 确定内容类型
                    if chunk.get("p") == "response/thinking_content":
                        ptype = "thinking"
                    elif chunk.get("p") == "response/content":
                        ptype = "text"

                    # 处理字符串内容
                    if isinstance(v_value, str):
                        content = v_value
                        if search_enabled and content.startswith("[citation:"):
                            continue
                        result_queue.put({"type": ptype, "content": content})

                    # 处理数组（状态变更）
                    elif isinstance(v_value, list):
                        for item in v_value:
                            if item.get("p") == "status" and item.get("v") == "FINISHED":
                                result_queue.put({"type": "finish"})
                                result_queue.put(None)
                                return
                        continue

                except json.JSONDecodeError:
                    logger.warning(f"[parse_stream] JSON 解析失败: {data_str[:100]}")
                    continue

    except Exception as e:
        logger.error(f"[parse_stream] 流解析异常: {e}")
    finally:
        deepseek_resp.close()
        result_queue.put(None)  # 确保有结束信号


# ======================== FastAPI 应用 ========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("DeepSeek2API 服务启动")
    logger.info(f"已配置 {len(CONFIG.get('accounts', []))} 个账号")
    logger.info(f"API Key: {CONFIG.get('api_key', '未设置')}")
    logger.info("=" * 50)
    yield


app = FastAPI(
    title="DeepSeek2API",
    description="将 DeepSeek 网页免费聊天转换为 OpenAI 兼容 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")


# ======================== 路由 ========================

@app.get("/")
async def welcome(request: Request):
    """欢迎页面"""
    return templates.TemplateResponse("welcome.html", {"request": request})


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "accounts_available": len(account_queue)}


@app.get("/v1/models")
async def list_models():
    """列出可用模型"""
    models_list = [
        {"id": "deepseek-chat", "object": "model", "created": 1677610602, "owned_by": "deepseek"},
        {"id": "deepseek-reasoner", "object": "model", "created": 1677610602, "owned_by": "deepseek"},
        {"id": "deepseek-chat-search", "object": "model", "created": 1677610602, "owned_by": "deepseek"},
        {"id": "deepseek-reasoner-search", "object": "model", "created": 1677610602, "owned_by": "deepseek"},
    ]
    return JSONResponse(content={"object": "list", "data": models_list})


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI 兼容的聊天补全接口"""

    # 认证
    try:
        authenticate(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": {"message": e.detail, "type": "auth_error"}})

    # 解析请求
    try:
        req_data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"message": "无效的 JSON 请求体", "type": "invalid_request"}})

    model = req_data.get("model", "deepseek-chat")
    messages = req_data.get("messages", [])
    stream = bool(req_data.get("stream", False))

    if not messages:
        return JSONResponse(status_code=400, content={"error": {"message": "messages 不能为空", "type": "invalid_request"}})

    # 获取模型配置
    model_cfg = MODEL_CONFIG.get(model.lower())
    if model_cfg is None:
        return JSONResponse(status_code=400, content={"error": {"message": f"不支持的模型: {model}", "type": "invalid_request"}})

    thinking_enabled = model_cfg["thinking"]
    search_enabled = model_cfg["search"]

    # 获取 token
    token = request.state.deepseek_token

    # 创建会话
    session_id = create_session(token)
    if not session_id:
        if request.state.use_config_token and request.state.account:
            release_account(request.state.account)
        return JSONResponse(status_code=401, content={"error": {"message": "创建会话失败，token 可能无效", "type": "auth_error"}})

    # 获取 PoW
    pow_resp = get_pow_response(token)
    if not pow_resp:
        delete_session(token, session_id)
        if request.state.use_config_token and request.state.account:
            release_account(request.state.account)
        return JSONResponse(status_code=401, content={"error": {"message": "获取 PoW 失败", "type": "auth_error"}})

    # 构造请求
    final_prompt = messages_prepare(messages)
    headers = {**get_auth_headers(request), "x-ds-pow-response": pow_resp}
    payload = {
        "chat_session_id": session_id,
        "parent_message_id": None,
        "prompt": final_prompt,
        "ref_file_ids": [],
        "thinking_enabled": thinking_enabled,
        "search_enabled": search_enabled,
    }

    # 调用补全接口
    deepseek_resp = call_completion(payload, headers)
    if not deepseek_resp:
        delete_session(token, session_id)
        if request.state.use_config_token and request.state.account:
            release_account(request.state.account)
        return JSONResponse(status_code=500, content={"error": {"message": "补全请求失败", "type": "server_error"}})

    # 发送遥测事件（后台线程，防封号）
    threading.Thread(
        target=send_events,
        args=(session_id, token, thinking_enabled),
        daemon=True,
    ).start()

    created_time = int(time.time())
    completion_id = session_id

    # ---------- 流式响应 ----------
    if stream:
        def sse_stream():
            final_text = ""
            final_thinking = ""
            first_chunk_sent = False
            result_queue = queue.Queue()
            last_send_time = time.time()

            # 启动后台解析线程
            parse_thread = threading.Thread(
                target=parse_deepseek_stream,
                args=(deepseek_resp, result_queue, thinking_enabled, search_enabled),
                daemon=True,
            )
            parse_thread.start()

            try:
                while True:
                    current_time = time.time()

                    # keep-alive
                    if current_time - last_send_time >= KEEP_ALIVE_TIMEOUT:
                        yield ": keep-alive\n\n"
                        last_send_time = current_time
                        continue

                    try:
                        item = result_queue.get(timeout=0.05)
                    except queue.Empty:
                        continue

                    # 结束信号
                    if item is None:
                        # 发送 finish chunk
                        prompt_tokens = len(final_prompt) // 4
                        thinking_tokens = len(final_thinking) // 4
                        completion_tokens = len(final_text) // 4

                        finish_chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model,
                            "choices": [{
                                "delta": {},
                                "index": 0,
                                "finish_reason": "stop",
                            }],
                            "usage": {
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": thinking_tokens + completion_tokens,
                                "total_tokens": prompt_tokens + thinking_tokens + completion_tokens,
                                "completion_tokens_details": {"reasoning_tokens": thinking_tokens},
                            },
                        }
                        yield f"data: {json.dumps(finish_chunk, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"
                        break

                    # finish 信号（来自数组中的 FINISHED）
                    if isinstance(item, dict) and item.get("type") == "finish":
                        prompt_tokens = len(final_prompt) // 4
                        thinking_tokens = len(final_thinking) // 4
                        completion_tokens = len(final_text) // 4

                        finish_chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model,
                            "choices": [{
                                "delta": {},
                                "index": 0,
                                "finish_reason": "stop",
                            }],
                            "usage": {
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": thinking_tokens + completion_tokens,
                                "total_tokens": prompt_tokens + thinking_tokens + completion_tokens,
                                "completion_tokens_details": {"reasoning_tokens": thinking_tokens},
                            },
                        }
                        yield f"data: {json.dumps(finish_chunk, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"
                        break

                    # 内容 chunk
                    if isinstance(item, dict) and "content" in item:
                        ctype = item["type"]
                        content = item["content"]

                        if ctype == "thinking" and thinking_enabled:
                            final_thinking += content
                        elif ctype == "text":
                            final_text += content
                        else:
                            continue

                        delta_obj = {}
                        if not first_chunk_sent:
                            delta_obj["role"] = "assistant"
                            first_chunk_sent = True

                        if ctype == "thinking" and thinking_enabled:
                            delta_obj["reasoning_content"] = content
                        elif ctype == "text":
                            delta_obj["content"] = content

                        if delta_obj:
                            out_chunk = {
                                "id": completion_id,
                                "object": "chat.completion.chunk",
                                "created": created_time,
                                "model": model,
                                "choices": [{"delta": delta_obj, "index": 0}],
                            }
                            yield f"data: {json.dumps(out_chunk, ensure_ascii=False)}\n\n"
                            last_send_time = current_time

            except GeneratorExit:
                logger.info(f"[sse_stream] 客户端断开连接 session={session_id}")
            finally:
                delete_session(token, session_id)
                if request.state.use_config_token and request.state.account:
                    release_account(request.state.account)

        return StreamingResponse(
            sse_stream(),
            media_type="text/event-stream",
            headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # ---------- 非流式响应 ----------
    else:
        text_list = []
        think_list = []
        result_queue = queue.Queue()

        parse_thread = threading.Thread(
            target=parse_deepseek_stream,
            args=(deepseek_resp, result_queue, thinking_enabled, search_enabled),
            daemon=True,
        )
        parse_thread.start()

        while True:
            try:
                item = result_queue.get(timeout=120)
            except queue.Empty:
                break

            if item is None:
                break

            if isinstance(item, dict):
                if item.get("type") == "finish":
                    break
                if "content" in item:
                    if item["type"] == "thinking" and thinking_enabled:
                        think_list.append(item["content"])
                    elif item["type"] == "text":
                        text_list.append(item["content"])

        final_content = "".join(text_list)
        final_reasoning = "".join(think_list)
        prompt_tokens = len(final_prompt) // 4
        reasoning_tokens = len(final_reasoning) // 4
        completion_tokens = len(final_content) // 4

        message_obj = {"role": "assistant", "content": final_content}
        if thinking_enabled and final_reasoning:
            message_obj["reasoning_content"] = final_reasoning

        result = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created_time,
            "model": model,
            "choices": [{
                "index": 0,
                "message": message_obj,
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": reasoning_tokens + completion_tokens,
                "total_tokens": prompt_tokens + reasoning_tokens + completion_tokens,
                "completion_tokens_details": {"reasoning_tokens": reasoning_tokens},
            },
        }

        delete_session(token, session_id)
        if request.state.use_config_token and request.state.account:
            release_account(request.state.account)

        return JSONResponse(content=result)


# ======================== 管理接口 ========================

@app.post("/admin/login")
async def admin_login(request: Request):
    """手动登录账号获取 token"""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "无效的 JSON"})

    account = {}
    if "email" in data:
        account["email"] = data["email"]
    elif "mobile" in data:
        account["mobile"] = data["mobile"]
    else:
        return JSONResponse(status_code=400, content={"error": "需要 email 或 mobile"})

    if "password" not in data:
        return JSONResponse(status_code=400, content={"error": "需要 password"})

    account["password"] = data["password"]

    try:
        token = login_deepseek(account)
        return {"status": "ok", "token": token, "account": get_account_id(account)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/admin/accounts")
async def admin_accounts():
    """查看账号状态"""
    accounts_info = []
    for acc in CONFIG.get("accounts", []):
        info = {
            "id": get_account_id(acc),
            "has_token": bool(acc.get("token", "").strip()),
        }
        accounts_info.append(info)
    return {"accounts": accounts_info, "queue_size": len(account_queue)}


@app.put("/admin/accounts")
async def update_accounts(request: Request):
    """替换全部账号配置（由 backend 同步调用）

    请求体: {"accounts": [{"email": "...", "password": "...", "token": "..."}, ...]}
    会同时更新内存中的 CONFIG/account_queue 以及 config.json 文件。
    """
    global CONFIG
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "无效的 JSON"})

    if "accounts" not in data or not isinstance(data["accounts"], list):
        return JSONResponse(status_code=400, content={"error": "需要 accounts 数组"})

    new_accounts = data["accounts"]

    # 更新 CONFIG 和 config.json
    CONFIG["accounts"] = new_accounts
    try:
        save_config(CONFIG)
        logger.info(f"[update_accounts] config.json 已更新，共 {len(new_accounts)} 个账号")
    except Exception as e:
        logger.warning(f"[update_accounts] 写入 config.json 失败 (可能为只读挂载): {e}")

    # 重建内存中的账号队列
    with queue_lock:
        account_queue.clear()
        account_queue.extend(new_accounts)
        random.shuffle(account_queue)

    return {
        "status": "ok",
        "total_accounts": len(new_accounts),
        "queue_size": len(account_queue),
    }


# ======================== 启动入口 ========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
