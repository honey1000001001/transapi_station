import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables, async_session
from app.models.user import User
from app.utils.security import hash_password
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Global references
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    global redis_client

    # --- Startup ---
    logger.info("Starting TransAPI Station backend...")

    # Create database tables
    await create_tables()
    logger.info("Database tables created/verified")

    # Create default admin user if not exists
    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                username="admin",
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
                balance=0,
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Default admin user created: {settings.ADMIN_EMAIL}")
        else:
            logger.info("Admin user already exists")

    # Initialize Redis connection
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        await redis_client.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Rate limiting will be disabled.")
        redis_client = None

    # Start httpx AsyncClient for upstream proxy
    app.state.http_client = httpx.AsyncClient(timeout=120.0)
    app.state.redis_client = redis_client
    logger.info(f"Upstream proxy client configured: {settings.UPSTREAM_BASE_URL}")

    logger.info("TransAPI Station backend started successfully")

    yield

    # --- Shutdown ---
    logger.info("Shutting down TransAPI Station backend...")

    # Close httpx client
    if hasattr(app.state, "http_client"):
        await app.state.http_client.aclose()

    # Close Redis
    if redis_client:
        await redis_client.close()

    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    from app.routers import auth, api_keys, proxy, billing, admin

    app.include_router(auth.router)
    app.include_router(api_keys.router)
    app.include_router(proxy.router)
    app.include_router(billing.router)
    app.include_router(admin.router)

    return app


app = create_app()
