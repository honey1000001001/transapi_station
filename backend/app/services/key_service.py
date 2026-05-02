import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import KeyCreated, KeyOut
from app.utils.security import generate_api_key, hash_api_key

logger = logging.getLogger(__name__)


async def create_key(
    db: AsyncSession, user: User, name: str, rpm_limit: int = 0, tpm_limit: int = 0
) -> KeyCreated:
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:8]

    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        is_active=True,
        rpm_limit=rpm_limit,
        tpm_limit=tpm_limit,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    logger.info(f"API key created: {key_prefix}... for user {user.username}")
    return KeyCreated(
        id=api_key.id,
        key=raw_key,
        key_prefix=key_prefix,
        name=api_key.name,
        is_active=api_key.is_active,
        rpm_limit=api_key.rpm_limit,
        tpm_limit=api_key.tpm_limit,
        created_at=api_key.created_at,
    )


async def list_keys(db: AsyncSession, user: User) -> list[KeyOut]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        KeyOut(
            id=k.id,
            key_prefix=k.key_prefix,
            name=k.name,
            is_active=k.is_active,
            rpm_limit=k.rpm_limit,
            tpm_limit=k.tpm_limit,
            total_requests=k.total_requests,
            total_tokens=k.total_tokens,
            created_at=k.created_at,
        )
        for k in keys
    ]


async def revoke_key(db: AsyncSession, user: User, key_id: str) -> bool:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        return False
    api_key.is_active = False
    await db.commit()
    logger.info(f"API key revoked: {api_key.key_prefix}...")
    return True


async def update_key(
    db: AsyncSession, user: User, key_id: str, **kwargs
) -> ApiKey | None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        return None

    for field, value in kwargs.items():
        if value is not None and hasattr(api_key, field):
            setattr(api_key, field, value)

    await db.commit()
    await db.refresh(api_key)
    return api_key


async def validate_key(db: AsyncSession, raw_key: str) -> ApiKey | None:
    """Look up API key by hash."""
    key_hash = hash_api_key(raw_key)
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    if api_key and api_key.is_active:
        return api_key
    return None
