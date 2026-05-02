from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.billing import InvoiceSummary, LogOut, RechargeRequest, UsageStats
from app.services import billing_service

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.get("/usage", response_model=UsageStats)
async def usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await billing_service.get_usage_stats(db, user)


@router.get("/logs")
async def logs(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, select
    from app.models.request_log import RequestLog
    total = (await db.execute(
        select(func.count(RequestLog.id)).where(RequestLog.user_id == user.id)
    )).scalar() or 0
    items = await billing_service.get_logs(db, user, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/balance")
async def balance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, select
    from app.models.payment import Payment
    from app.models.request_log import RequestLog
    await db.refresh(user)
    total_recharged = (await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.user_id == user.id)
    )).scalar() or 0
    total_consumed = (await db.execute(
        select(func.coalesce(func.sum(RequestLog.cost), 0)).where(RequestLog.user_id == user.id)
    )).scalar() or 0
    return {
        "balance": float(user.balance),
        "total_recharged": float(total_recharged),
        "total_consumed": float(total_consumed),
    }


@router.post("/recharge")
async def recharge(
    req: RechargeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await billing_service.recharge(db, user, req.code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


@router.get("/invoices", response_model=list[InvoiceSummary])
async def invoices(
    period: str = "daily",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await billing_service.get_invoices(db, user, period)
