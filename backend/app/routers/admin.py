from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_admin
from app.models.user import User
from app.schemas.admin import (
    AdminUserOut,
    AdminUserUpdate,
    RechargeCodeGenerate,
    StatsResponse,
    UpstreamAccountCreate,
    UpstreamAccountOut,
    UpstreamAccountUpdate,
)
from app.services import admin_service, payment_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# --- Users ---
@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, select
    from app.models.user import User as UserModel
    from sqlalchemy import or_

    base_q = select(UserModel)
    if search:
        base_q = base_q.where(or_(UserModel.username.contains(search), UserModel.email.contains(search)))

    total_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(base_q.order_by(UserModel.created_at.desc()).offset(offset).limit(page_size))
    users = result.scalars().all()
    items = [
        AdminUserOut(
            id=u.id, username=u.username, email=u.email,
            role=u.role, balance=float(u.balance), is_active=u.is_active,
            created_at=u.created_at,
        ) for u in users
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/users/{user_id}", response_model=AdminUserOut)
async def get_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await admin_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"error": "User not found"})
    return user


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: str,
    data: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await admin_service.update_user(db, user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail={"error": "User not found"})
    return AdminUserOut(
        id=user.id, username=user.username, email=user.email,
        role=user.role, balance=float(user.balance), is_active=user.is_active,
        created_at=user.created_at,
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    success = await admin_service.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail={"error": "User not found"})
    return {"message": "User deleted"}


# --- Upstream Accounts ---
@router.get("/upstream-accounts")
async def list_upstream_accounts(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, select
    from app.models.upstream_account import UpstreamAccount as UAModel
    total = (await db.execute(select(func.count(UAModel.id)))).scalar() or 0
    items = await admin_service.list_upstream_accounts(db)
    # items 已经是 UpstreamAccountOut 列表，直接 model_dump 序列化
    return {"items": [i.model_dump() for i in items], "total": total}


@router.post("/upstream-accounts")
async def add_upstream_account(
    data: UpstreamAccountCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if not data.password and not data.token:
        raise HTTPException(
            status_code=400,
            detail={"error": "请至少填写密码（账号池模式）或Token（直连模式）"},
        )
    if data.token and not data.email:
        # 直连Token模式下如果没有邮箱，自动生成一个标识
        data.email = f"token-{__import__('uuid').uuid4().hex[:8]}@direct"
    if data.password and not data.email:
        raise HTTPException(
            status_code=400,
            detail={"error": "账号池模式必须填写邮箱"},
        )
    result = await admin_service.add_upstream_account(db, data)
    return result.model_dump()


@router.patch("/upstream-accounts/{account_id}", response_model=UpstreamAccountOut)
async def update_upstream_account(
    account_id: str,
    data: UpstreamAccountUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    account = await admin_service.update_upstream_account(db, account_id, data)
    if not account:
        raise HTTPException(status_code=404, detail={"error": "Upstream account not found"})
    return account


@router.delete("/upstream-accounts/{account_id}")
async def delete_upstream_account(
    account_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    success = await admin_service.delete_upstream_account(db, account_id)
    if not success:
        raise HTTPException(status_code=404, detail={"error": "Upstream account not found"})
    return {"message": "Upstream account deleted"}


@router.post("/upstream-accounts/{account_id}/health-check")
async def health_check_upstream(
    account_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select as sq
    from app.models.upstream_account import UpstreamAccount
    result = await db.execute(sq(UpstreamAccount).where(UpstreamAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail={"error": "Account not found"})
    health = await admin_service.check_upstream_health(account)
    account.health = health
    await db.commit()
    return {"id": account_id, "health": health}


@router.post("/upstream-accounts/sync")
async def sync_upstream_accounts(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """将数据库中的账号池模式账号同步到 proxy_web_api 的 config.json。"""
    return await admin_service.sync_to_upstream_proxy(db)


@router.post("/upstream-accounts/validate-token")
async def validate_upstream_token(
    data: dict,
    admin: User = Depends(require_admin),
):
    """验证一个 DeepSeek 浏览器 Token 是否有效。"""
    token = data.get("token", "")
    if not token:
        raise HTTPException(status_code=400, detail={"error": "请提供 Token"})
    return await admin_service.validate_upstream_token(token)


@router.post("/upstream-accounts/{account_id}/login")
async def trigger_upstream_login(
    account_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """触发 proxy_web_api 对指定账号执行登录获取 token。"""
    from sqlalchemy import select as sq
    from app.models.upstream_account import UpstreamAccount
    result = await db.execute(sq(UpstreamAccount).where(UpstreamAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail={"error": "Account not found"})
    if not account.password_enc:
        raise HTTPException(status_code=400, detail={"error": "该账号未配置密码，无法执行登录"})
    return await admin_service.trigger_upstream_login(account)


# --- Recharge Codes ---
@router.post("/recharge-codes")
async def generate_recharge_codes(
    data: RechargeCodeGenerate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    codes = await payment_service.create_recharge_codes(db, admin, data)
    return {"codes": codes, "count": len(codes)}


@router.get("/recharge-codes")
async def list_recharge_codes(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await payment_service.list_recharge_codes(db, page, page_size)
    if status:
        items = [c for c in items if (c.get("used_by") is not None) == (status == "used")]
    total = len(items)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# --- Rate Limits ---
@router.get("/rate-limits")
async def list_rate_limits(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return [
        {"id": "global", "scope": "global", "target_id": None, "rpm": 60, "tpm": 100000}
    ]


@router.post("/rate-limits")
async def create_rate_limit(
    data: dict,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return data


@router.patch("/rate-limits/{limit_id}")
async def update_rate_limit(
    limit_id: str,
    data: dict,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return {"id": limit_id, **data}


# --- Stats ---
@router.get("/stats", response_model=StatsResponse)
async def stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_stats(db)


# --- Payments ---
@router.get("/payments")
async def payments(
    page: int = 1,
    page_size: int = 20,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, select
    from app.models.payment import Payment as PayModel
    total = (await db.execute(select(func.count(PayModel.id)))).scalar() or 0
    items = await payment_service.list_payments(db, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}
