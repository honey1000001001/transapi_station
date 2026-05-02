import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.proxy_service import proxy_chat_completions, proxy_models
from app.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["proxy"])


@router.post("/api/v1/chat/completions")
async def chat_completions(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Extract API key from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail={"error": "Missing or invalid Authorization header"}
        )
    raw_key = auth_header[7:]

    # Parse request body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "Invalid JSON body"})

    # Get httpx client and rate limiter from app state
    http_client = request.app.state.http_client
    redis_client = getattr(request.app.state, "redis_client", None)
    rate_limiter = RateLimiter(redis_client)

    return await proxy_chat_completions(db, raw_key, body, rate_limiter, http_client)


@router.get("/api/v1/models")
async def models(request: Request):
    http_client = request.app.state.http_client
    data = await proxy_models(http_client)
    return JSONResponse(content=data)
