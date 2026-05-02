import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.payment import Payment
from app.models.upstream_account import UpstreamAccount
from app.models.user import User
from app.schemas.admin import (
    AdminUserOut,
    AdminUserUpdate,
    StatsResponse,
    UpstreamAccountCreate,
    UpstreamAccountOut,
    UpstreamAccountUpdate,
)
from app.config import settings
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)


# ---- Simple encrypt/decrypt for upstream account passwords ----
import base64, hashlib

def _encrypt_password(plain: str) -> str:
    """Simple reversible encryption for upstream account passwords.
    Uses a key derived from JWT_SECRET for encryption."""
    key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    raw = plain.encode("utf-8")
    # XOR with key bytes (cycling)
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return base64.b64encode(encrypted).decode("ascii")


def _decrypt_password(encrypted: str) -> str:
    """Decrypt a password encrypted by _encrypt_password."""
    key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    raw = base64.b64decode(encrypted)
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return decrypted.decode("utf-8")


def _account_to_out(account: UpstreamAccount) -> UpstreamAccountOut:
    """Convert UpstreamAccount model to UpstreamAccountOut schema."""
    has_password = account.password_enc is not None and account.password_enc != ""
    has_token = account.token is not None and account.token != ""
    auth_mode = "unknown"
    if has_token:
        auth_mode = "direct"  # 直连Token模式
    elif has_password:
        auth_mode = "pool"  # 账号池模式
    token_preview = None
    if has_token and account.token:
        token_preview = account.token[:8] + "..." + account.token[-4:]

    return UpstreamAccountOut(
        id=account.id,
        email=account.email,
        mobile=account.mobile,
        has_password=has_password,
        has_token=has_token,
        auth_mode=auth_mode,
        status=account.status,
        health=account.health,
        weight=account.weight,
        total_requests=account.total_requests,
        last_used_at=account.last_used_at,
        last_error=account.last_error,
        token_preview=token_preview,
        created_at=account.created_at,
    )


async def list_users(db: AsyncSession, page: int = 1, page_size: int = 20) -> list[AdminUserOut]:
    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()
    return [
        AdminUserOut(
            id=u.id, username=u.username, email=u.email,
            role=u.role, balance=float(u.balance),
            is_active=u.is_active, created_at=u.created_at,
        )
        for u in users
    ]


async def get_user(db: AsyncSession, user_id: str) -> AdminUserOut | None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    return AdminUserOut(
        id=user.id, username=user.username, email=user.email,
        role=user.role, balance=float(user.balance),
        is_active=user.is_active, created_at=user.created_at,
    )


async def update_user(db: AsyncSession, user_id: str, data: AdminUserUpdate) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    if data.username is not None:
        user.username = data.username
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        user.role = data.role
    if data.balance is not None:
        user.balance = Decimal(str(data.balance))
    if data.is_active is not None:
        user.is_active = data.is_active
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False
    await db.delete(user)
    await db.commit()
    return True


async def list_upstream_accounts(db: AsyncSession) -> list[UpstreamAccountOut]:
    result = await db.execute(select(UpstreamAccount).order_by(UpstreamAccount.created_at))
    accounts = result.scalars().all()
    return [_account_to_out(a) for a in accounts]


async def add_upstream_account(
    db: AsyncSession, data: UpstreamAccountCreate
) -> UpstreamAccountOut:
    # Encrypt password if provided
    password_enc = None
    if data.password:
        password_enc = _encrypt_password(data.password)

    account = UpstreamAccount(
        email=data.email,
        mobile=data.mobile,
        password_enc=password_enc,
        token=data.token,
        weight=data.weight,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return _account_to_out(account)


async def update_upstream_account(
    db: AsyncSession, account_id: str, data: UpstreamAccountUpdate
) -> UpstreamAccountOut | None:
    result = await db.execute(select(UpstreamAccount).where(UpstreamAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        return None

    if data.email is not None:
        account.email = data.email
    if data.mobile is not None:
        account.mobile = data.mobile
    if data.password is not None:
        account.password_enc = _encrypt_password(data.password)
    if data.token is not None:
        account.token = data.token
    if data.status is not None:
        account.status = data.status
    if data.health is not None:
        account.health = data.health
    if data.weight is not None:
        account.weight = data.weight

    await db.commit()
    await db.refresh(account)
    return _account_to_out(account)


async def delete_upstream_account(db: AsyncSession, account_id: str) -> bool:
    result = await db.execute(select(UpstreamAccount).where(UpstreamAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        return False
    await db.delete(account)
    await db.commit()
    return True


async def sync_to_upstream_proxy(db: AsyncSession) -> dict:
    """将数据库中所有 active 上游账号同步到 proxy-web-api。
    
    通过 HTTP API (PUT /admin/accounts) 更新上游服务的账号列表，
    上游服务会同时更新内存队列和 config.json 文件。
    
    Returns:
        dict: {"synced": count, "errors": [...]}
    """
    result = await db.execute(
        select(UpstreamAccount).where(UpstreamAccount.status == "active")
    )
    all_accounts = result.scalars().all()

    accounts_data = []
    errors = []
    for acc in all_accounts:
        password = ""
        if acc.password_enc:
            try:
                password = _decrypt_password(acc.password_enc)
            except Exception:
                logger.warning("Failed to decrypt password for %s", acc.email)
                errors.append(f"账号 {acc.email} 密码解密失败，已跳过")
                continue
        accounts_data.append({
            "email": acc.email or "",
            "password": password,
            "token": acc.token or "",
        })

    synced = 0
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{settings.UPSTREAM_BASE_URL}/admin/accounts",
                json={"accounts": accounts_data},
            )
            if resp.status_code == 200:
                result = resp.json()
                synced = result.get("total_accounts", len(accounts_data))
                logger.info("Synced %d accounts to upstream proxy", synced)
            else:
                errors.append(f"上游服务返回错误: HTTP {resp.status_code} - {resp.text[:200]}")
    except httpx.ConnectError:
        errors.append(f"无法连接到上游服务 ({settings.UPSTREAM_BASE_URL})，请确认 proxy-web-api 正在运行")
    except Exception as e:
        errors.append(f"同步请求失败: {str(e)}")

    return {"synced": synced, "total_accounts": len(accounts_data), "errors": errors}


async def validate_upstream_token(token: str) -> dict:
    """验证一个 DeepSeek 浏览器 Token 是否有效。
    
    通过 proxy_web_api 发送一个简单请求来验证。
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.UPSTREAM_BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                    "max_tokens": 5,
                },
            )
            if resp.status_code == 200:
                return {"valid": True, "message": "Token 有效"}
            else:
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("error", {}).get("message", resp.text[:200])
                except Exception:
                    error_msg = resp.text[:200]
                return {"valid": False, "message": f"Token 无效: {error_msg}"}
    except Exception as e:
        return {"valid": False, "message": f"验证请求失败: {str(e)}"}


async def trigger_upstream_login(account: UpstreamAccount) -> dict:
    """触发 proxy_web_api 对指定账号执行登录获取 token。
    
    proxy_web_api 的 /admin/login 端点需要 email + password，
    所以我们必须解密密码后一起发送过去。
    登录成功后，proxy_web_api 会自动更新 config.json 中的 token，
    同时我们也需要将新 token 回写到数据库。
    """
    # 解密密码
    try:
        password = _decrypt_password(account.password_enc) if account.password_enc else ""
    except Exception:
        return {"error": "密码解密失败，无法执行登录"}

    if not password:
        return {"error": "该账号未配置密码，无法执行登录"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 构建与 proxy_web_api /admin/login 匹配的请求体
            login_payload: dict = {"password": password}
            if account.email and not account.email.startswith("token-"):
                login_payload["email"] = account.email
            elif account.mobile:
                login_payload["mobile"] = account.mobile
            else:
                return {"error": "账号缺少邮箱或手机号，无法登录"}

            resp = await client.post(
                f"{settings.UPSTREAM_BASE_URL}/admin/login",
                json=login_payload,
            )
            result = resp.json()

            # 如果登录成功且返回了 token，回写到数据库
            if resp.status_code == 200 and result.get("token"):
                from app.database import async_session
                async with async_session() as db:
                    db_account = await db.get(UpstreamAccount, account.id)
                    if db_account:
                        db_account.token = result["token"]
                        await db.commit()
                return {
                    "status": "ok",
                    "token_preview": result["token"][:8] + "..." + result["token"][-4:],
                    "account": result.get("account", account.email),
                }

            return result
    except Exception as e:
        return {"error": f"登录请求失败: {str(e)}"}


async def get_stats(db: AsyncSession) -> StatsResponse:
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
    active_keys = (await db.execute(select(func.count(ApiKey.id)).where(ApiKey.is_active == True))).scalar() or 0
    active_upstream = (await db.execute(select(func.count(UpstreamAccount.id)).where(UpstreamAccount.status == "active"))).scalar() or 0

    from app.models.request_log import RequestLog
    total_requests = (await db.execute(select(func.count(RequestLog.id)))).scalar() or 0
    total_tokens = (await db.execute(
        select(func.coalesce(func.sum(RequestLog.prompt_tokens + RequestLog.completion_tokens), 0))
    )).scalar() or 0
    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(RequestLog.cost), 0))
    )).scalar() or 0
    total_balance = (await db.execute(
        select(func.coalesce(func.sum(User.balance), 0))
    )).scalar() or 0

    return StatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_requests=total_requests,
        total_tokens=int(total_tokens),
        total_revenue=float(total_revenue),
        total_balance=float(total_balance),
        active_keys=active_keys,
        active_upstream_accounts=active_upstream,
    )


async def check_upstream_health(account: UpstreamAccount) -> str:
    """Ping the upstream proxy's /health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.UPSTREAM_BASE_URL}/health")
            if resp.status_code == 200:
                return "healthy"
            return "degraded"
    except Exception as e:
        logger.warning("Upstream health check failed for %s: %s", account.email, e)
        return "down"
