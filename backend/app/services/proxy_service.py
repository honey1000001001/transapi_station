import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.api_key import ApiKey
from app.models.request_log import RequestLog
from app.models.upstream_account import UpstreamAccount
from app.models.user import User
from app.services.key_service import validate_key
from app.services.rate_limiter import RateLimiter
from app.utils.security import hash_api_key

logger = logging.getLogger(__name__)

# Pricing per 1K tokens (input, output)
PRICING = {
    "deepseek-chat": (Decimal("0.001"), Decimal("0.002")),
    "deepseek-reasoner": (Decimal("0.002"), Decimal("0.006")),
    "deepseek-chat-search": (Decimal("0.002"), Decimal("0.004")),
    "deepseek-reasoner-search": (Decimal("0.004"), Decimal("0.012")),
}

# Weighted round-robin state
_rr_index = 0


def _get_pricing(model: str) -> tuple[Decimal, Decimal]:
    """Get input/output pricing for a model. Default to deepseek-chat pricing."""
    return PRICING.get(model, PRICING["deepseek-chat"])


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    """Calculate cost based on model pricing."""
    input_price, output_price = _get_pricing(model)
    cost = (Decimal(prompt_tokens) / 1000 * input_price) + (
        Decimal(completion_tokens) / 1000 * output_price
    )
    return cost


def _estimate_max_cost(model: str, prompt_tokens: int) -> Decimal:
    """Estimate maximum possible cost for balance pre-check (assume 4x prompt as output)."""
    estimated_output = prompt_tokens * 4
    return _estimate_cost(model, prompt_tokens, estimated_output)


async def _select_upstream_account(
    db: AsyncSession,
) -> UpstreamAccount | None:
    """Select an upstream account using weighted round-robin."""
    global _rr_index
    result = await db.execute(
        select(UpstreamAccount)
        .where(UpstreamAccount.status == "active")
        .order_by(UpstreamAccount.weight.desc())
    )
    accounts = result.scalars().all()
    if not accounts:
        return None

    # Weighted selection
    total_weight = sum(a.weight for a in accounts)
    if total_weight == 0:
        return accounts[0]

    # Simple weighted round-robin
    _rr_index = _rr_index % len(accounts)
    account = accounts[_rr_index]
    _rr_index = (_rr_index + 1) % len(accounts)
    return account


def _extract_token_counts(data: dict) -> tuple[int, int, int]:
    """Extract prompt_tokens, completion_tokens, reasoning_tokens from response."""
    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    # Try to extract reasoning tokens from completion_tokens_details
    reasoning_tokens = 0
    details = usage.get("completion_tokens_details", {})
    if isinstance(details, dict):
        reasoning_tokens = details.get("reasoning_tokens", 0)

    # Fallback: estimate from content if upstream returns 0 tokens
    # (happens with very short replies where DeepSeek reports 0 completion tokens)
    choices = data.get("choices", [])
    content = ""
    reasoning_content = ""
    for choice in choices:
        message = choice.get("message", choice.get("delta", {}))
        content += (message.get("content", "") or "")
        reasoning_content += (message.get("reasoning_content", "") or "")

    if prompt_tokens == 0:
        prompt_tokens = max(1, (len(content) + len(reasoning_content)) // 4)
    if completion_tokens == 0 and content:
        completion_tokens = max(1, len(content) // 4)
    if reasoning_tokens == 0 and reasoning_content:
        reasoning_tokens = max(1, len(reasoning_content) // 4)

    return prompt_tokens, completion_tokens, reasoning_tokens


async def proxy_chat_completions(
    db: AsyncSession,
    raw_key: str,
    request_body: dict,
    rate_limiter: RateLimiter,
    http_client: httpx.AsyncClient,
) -> StreamingResponse | dict:
    """Core proxy logic: auth -> rate limit -> balance check -> forward -> bill -> return."""
    start_time = time.time()

    # 1. Validate API key
    api_key = await validate_key(db, raw_key)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid API key"},
        )

    # 2. Get user
    result = await db.execute(select(User).where(User.id == api_key.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "User account is disabled"},
        )

    # 3. Rate limit check
    if not await rate_limiter.check_rpm(api_key.id, api_key.rpm_limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "Rate limit exceeded: RPM limit"},
        )

    model = request_body.get("model", "deepseek-chat")
    is_stream = request_body.get("stream", False)

    # Estimate prompt tokens from request for TPM pre-check and balance check
    messages = request_body.get("messages", [])
    estimated_prompt_tokens = sum(
        len(str(m.get("content", ""))) // 4 for m in messages
    ) or 100

    if not await rate_limiter.check_tpm(
        api_key.id, estimated_prompt_tokens, api_key.tpm_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "Rate limit exceeded: TPM limit"},
        )

    # 5. Balance pre-check
    estimated_cost = _estimate_max_cost(model, estimated_prompt_tokens)
    if Decimal(str(user.balance)) < estimated_cost * Decimal("0.1"):
        # Very lenient: only reject if balance is less than 10% of estimated cost
        if Decimal(str(user.balance)) <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"error": "Insufficient balance"},
            )

    # 6. Select upstream account
    upstream_account = await _select_upstream_account(db)

    # Build upstream request headers
    # Priority: 1) upstream_account.token (direct browser token mode)
    #           2) UPSTREAM_API_KEY (proxy_web_api account-pool mode)
    headers = {"Content-Type": "application/json"}
    if upstream_account and upstream_account.token:
        # Direct token mode: pass the DeepSeek browser token directly
        headers["Authorization"] = f"Bearer {upstream_account.token}"
    elif settings.UPSTREAM_API_KEY:
        # Account pool mode: use proxy_web_api's configured api_key
        headers["Authorization"] = f"Bearer {settings.UPSTREAM_API_KEY}"
    else:
        # No upstream account or API key available
        logger.error("No upstream account available and UPSTREAM_API_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "暂无可用上游账号，请联系管理员"},
        )

    upstream_url = f"{settings.UPSTREAM_BASE_URL}/v1/chat/completions"

    # 7-12. Forward request
    if is_stream:
        return await _handle_streaming(
            db, user, api_key, upstream_account, request_body,
            headers, upstream_url, http_client, start_time, model
        )
    else:
        return await _handle_non_streaming(
            db, user, api_key, upstream_account, request_body,
            headers, upstream_url, http_client, start_time, model
        )


def _map_upstream_error(status_code: int, raw_body: str) -> tuple[int, str]:
    """Map upstream HTTP error status/body to a user-friendly Chinese message.

    Returns (http_status_to_return, user_friendly_error_message).
    The raw body is always logged separately; the returned message is what the
    end-user sees.
    """
    if status_code in (401, 403):
        return status_code, "上游服务认证失败，请联系管理员"
    if status_code == 402:
        return status_code, "上游服务额度不足，请联系管理员"
    if status_code == 429:
        return status_code, "上游服务请求过快，请稍后重试"
    if status_code == 404:
        return status_code, "上游服务接口不存在，请检查模型名称"
    if 500 <= status_code < 600:
        return status_code, "上游服务内部错误，请稍后重试"
    # Fallback for any other unexpected status
    return status_code, f"上游服务返回错误 (HTTP {status_code})，请联系管理员"


async def _handle_non_streaming(
    db, user, api_key, upstream_account, request_body,
    headers, upstream_url, http_client, start_time, model
) -> dict:
    """Handle non-streaming request."""
    try:
        resp = await http_client.post(
            upstream_url, json=request_body, headers=headers, timeout=120.0
        )
        latency_ms = int((time.time() - start_time) * 1000)

        if resp.status_code != 200:
            raw_error = resp.text[:500]
            mapped_status, user_msg = _map_upstream_error(resp.status_code, raw_error)
            logger.warning(
                "Upstream non-streaming error: status=%d raw=%s",
                resp.status_code, raw_error,
            )
            await _write_log(
                db, user, api_key, model, 0, 0, 0,
                Decimal("0"), latency_ms, "error", raw_error, upstream_account
            )
            raise HTTPException(
                status_code=mapped_status,
                detail={"error": user_msg},
            )

        data = resp.json()
        prompt_tokens, completion_tokens, reasoning_tokens = _extract_token_counts(data)
        cost = _estimate_cost(model, prompt_tokens, completion_tokens)

        # Write log and deduct balance
        await _write_log(
            db, user, api_key, model, prompt_tokens, completion_tokens,
            reasoning_tokens, cost, latency_ms, "success", None, upstream_account
        )
        await _deduct_balance(db, user, cost)
        await _update_key_stats(db, api_key, prompt_tokens + completion_tokens)

        # Update upstream account stats
        if upstream_account:
            await _update_upstream_stats(db, upstream_account)

        return data

    except HTTPException:
        raise
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        err_str = str(e)[:500]
        logger.error("Proxy non-streaming exception: %s", err_str)
        await _write_log(
            db, user, api_key, model, 0, 0, 0,
            Decimal("0"), latency_ms, "error", err_str, upstream_account
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "上游服务连接异常，请稍后重试"},
        )


async def _handle_streaming(
    db, user, api_key, upstream_account, request_body,
    headers, upstream_url, http_client, start_time, model
) -> StreamingResponse:
    """Handle streaming request with token counting."""

    async def stream_generator():
        prompt_tokens = 0
        completion_tokens = 0
        reasoning_tokens = 0
        error_msg = None
        upstream_status = None

        try:
            async with http_client.stream(
                "POST", upstream_url, json=request_body, headers=headers, timeout=180.0
            ) as resp:
                if resp.status_code != 200:
                    upstream_status = resp.status_code
                    error_body = await resp.aread()
                    raw_error = error_body.decode()[:500]
                    _, user_msg = _map_upstream_error(resp.status_code, raw_error)
                    logger.warning(
                        "Upstream streaming error: status=%d raw=%s",
                        resp.status_code, raw_error,
                    )
                    # Store raw error for logging; send user-friendly message to client
                    error_msg = raw_error
                    yield f'data: {json.dumps({"error": {"message": user_msg, "type": "upstream_error", "code": resp.status_code}})}\n\n'
                    return

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            chunk = json.loads(data_str)
                            # Extract token counts from chunks
                            usage = chunk.get("usage", {})
                            if usage:
                                prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                                completion_tokens = usage.get("completion_tokens", completion_tokens)
                                details = usage.get("completion_tokens_details", {})
                                if isinstance(details, dict):
                                    reasoning_tokens = details.get("reasoning_tokens", reasoning_tokens)

                            # Count content tokens from delta
                            choices = chunk.get("choices", [])
                            for choice in choices:
                                delta = choice.get("delta", {})
                                content = delta.get("content", "") or ""
                                reasoning = delta.get("reasoning_content", "") or ""
                                if content:
                                    completion_tokens += max(1, len(content) // 4)
                                if reasoning:
                                    reasoning_tokens += max(1, len(reasoning) // 4)
                        except json.JSONDecodeError:
                            pass

                        yield line + "\n\n"
                    elif line.strip():
                        yield line + "\n\n"

        except Exception as e:
            error_msg = str(e)[:500]
            logger.error("Streaming exception: %s", error_msg)
            yield f'data: {json.dumps({"error": {"message": "上游服务连接异常，请稍后重试", "type": "upstream_connection_error", "code": 502}})}\n\n'

        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            cost = _estimate_cost(model, prompt_tokens, completion_tokens)

            if prompt_tokens == 0:
                messages = request_body.get("messages", [])
                prompt_tokens = sum(len(str(m.get("content", ""))) // 4 for m in messages) or 1

            if error_msg:
                await _write_log(
                    db, user, api_key, model, prompt_tokens, completion_tokens,
                    reasoning_tokens, cost, latency_ms, "error", error_msg, upstream_account
                )
            else:
                await _write_log(
                    db, user, api_key, model, prompt_tokens, completion_tokens,
                    reasoning_tokens, cost, latency_ms, "success", None, upstream_account
                )
                await _deduct_balance(db, user, cost)
                await _update_key_stats(db, api_key, prompt_tokens + completion_tokens)
                if upstream_account:
                    await _update_upstream_stats(db, upstream_account)

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _write_log(
    db, user, api_key, model, prompt_tokens, completion_tokens,
    reasoning_tokens, cost, latency_ms, status_str, error_message, upstream_account
):
    """Write request log entry."""
    log = RequestLog(
        user_id=user.id,
        api_key_id=api_key.id,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        reasoning_tokens=reasoning_tokens,
        cost=float(cost),
        latency_ms=latency_ms,
        status=status_str,
        error_message=error_message,
        upstream_account_id=upstream_account.id if upstream_account else None,
    )
    db.add(log)
    await db.commit()


async def _deduct_balance(db, user, cost):
    """Deduct cost from user balance."""
    user.balance = Decimal(str(user.balance)) - cost
    await db.commit()


async def _update_key_stats(db, api_key, tokens):
    """Update API key usage stats."""
    api_key.total_requests += 1
    api_key.total_tokens += tokens
    await db.commit()


async def _update_upstream_stats(db, account):
    """Update upstream account usage stats."""
    account.total_requests += 1
    account.last_used_at = datetime.now(timezone.utc)
    await db.commit()


async def proxy_models(http_client: httpx.AsyncClient) -> dict:
    """Forward /v1/models to upstream."""
    headers = {}
    if settings.UPSTREAM_API_KEY:
        headers["Authorization"] = f"Bearer {settings.UPSTREAM_API_KEY}"
    try:
        resp = await http_client.get(
            f"{settings.UPSTREAM_BASE_URL}/v1/models", headers=headers, timeout=10.0
        )
        if resp.status_code in (401, 403):
            logger.error("Upstream /models auth failed: status=%d", resp.status_code)
            # Return default models list instead of failing
        elif resp.status_code != 200:
            logger.warning("Upstream /models error: status=%d body=%s", resp.status_code, resp.text[:200])
        else:
            return resp.json()
    except Exception as e:
        logger.error("Failed to get models from upstream: %s", e)
    # Return default models list as fallback
    return {
        "object": "list",
        "data": [
            {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
            {"id": "deepseek-reasoner", "object": "model", "owned_by": "deepseek"},
            {"id": "deepseek-chat-search", "object": "model", "owned_by": "deepseek"},
            {"id": "deepseek-reasoner-search", "object": "model", "owned_by": "deepseek"},
        ],
    }
