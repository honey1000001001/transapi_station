import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import TokenResponse, LoginResponse, UserResponse
from app.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import settings

logger = logging.getLogger(__name__)


async def register(
    db: AsyncSession, username: str, email: str, password: str
) -> User:
    # Check duplicate username
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise ValueError("Username already exists")

    # Check duplicate email
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ValueError("Email already exists")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role="user",
        balance=0,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"User registered: {username} ({email})")
    return user


async def login(db: AsyncSession, email: str, password: str) -> LoginResponse:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")

    if not user.is_active:
        raise ValueError("Account is disabled")

    token = create_access_token({"sub": user.id, "role": user.role})
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRY_MINUTES * 60,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            balance=float(user.balance),
            is_active=user.is_active,
        ),
    )


async def get_me(db: AsyncSession, user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        balance=float(user.balance),
        is_active=user.is_active,
    )
