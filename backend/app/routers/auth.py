from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, LoginResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.register(db, req.username, req.email, req.password)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            balance=float(user.balance),
            is_active=user.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await auth_service.login(db, req.email, req.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail={"error": str(e)})


@router.get("/me", response_model=UserResponse)
async def me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.get_me(db, user)
