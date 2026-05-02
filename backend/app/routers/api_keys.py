from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.api_key import KeyCreate, KeyCreated, KeyOut, KeyUpdate
from app.services import key_service

router = APIRouter(prefix="/api/v1/keys", tags=["api-keys"])


@router.get("", response_model=list[KeyOut])
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await key_service.list_keys(db, user)


@router.post("", response_model=KeyCreated)
async def create_key(
    req: KeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await key_service.create_key(db, user, req.name, req.rpm_limit, req.tpm_limit)


@router.delete("/{key_id}")
async def revoke_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await key_service.revoke_key(db, user, key_id)
    if not success:
        raise HTTPException(status_code=404, detail={"error": "API key not found"})
    return {"message": "API key revoked"}


@router.patch("/{key_id}", response_model=KeyOut)
async def update_key(
    key_id: str,
    req: KeyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    update_data = req.model_dump(exclude_unset=True)
    api_key = await key_service.update_key(db, user, key_id, **update_data)
    if not api_key:
        raise HTTPException(status_code=404, detail={"error": "API key not found"})
    return KeyOut(
        id=api_key.id,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        is_active=api_key.is_active,
        rpm_limit=api_key.rpm_limit,
        tpm_limit=api_key.tpm_limit,
        total_requests=api_key.total_requests,
        total_tokens=api_key.total_tokens,
        created_at=api_key.created_at,
    )
