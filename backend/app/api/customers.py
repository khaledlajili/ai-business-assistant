from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.auth import UserOut
from app.schemas.customers import (
    CustomerSearchResult, CustomerSummary, SalesSummary, InactiveHighValueCustomer
)
from app.services.customer_service import CustomerService, PermissionDenied
from app.services.audit import log_audit
from app.core.clock import Clock

router = APIRouter(tags=["customers"])


@router.get("/customers/search", response_model=list[CustomerSearchResult])
async def search_customers(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CustomerService(db)
    try:
        results = await svc.search(current_user.workspace_id, current_user.role, q, limit)
    except PermissionDenied as e:
        await log_audit(db, action="permission_denied", user_id=current_user.id,
                        workspace_id=current_user.workspace_id, details=str(e))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return results


@router.get("/customers/{customer_id}/summary", response_model=CustomerSummary)
async def customer_summary(
    customer_id: UUID,
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CustomerService(db)
    try:
        result = await svc.get_summary(current_user.workspace_id, current_user.role, customer_id)
    except PermissionDenied as e:
        await log_audit(db, action="permission_denied", user_id=current_user.id,
                        workspace_id=current_user.workspace_id, details=str(e))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if result is None:
        # Return 404 for both "not found" and "wrong workspace" (anti-enumeration)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return result


@router.get("/sales/summary", response_model=SalesSummary)
async def sales_summary(
    period: str = Query(..., pattern="^(previous_month|current_month|last_30_days)$"),
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CustomerService(db)
    try:
        result = await svc.sales_summary(current_user.workspace_id, current_user.role, period)
    except PermissionDenied as e:
        await log_audit(db, action="permission_denied", user_id=current_user.id,
                        workspace_id=current_user.workspace_id, details=str(e))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return result


@router.get("/sales/inactive-high-value", response_model=list[InactiveHighValueCustomer])
async def inactive_high_value(
    minimum_spend: Decimal = Query(Decimal("500.000")),
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CustomerService(db)
    try:
        results = await svc.find_inactive_high_value(
            current_user.workspace_id,
            current_user.role,
            minimum_spend,
            timezone="Africa/Tunis",
        )
    except PermissionDenied as e:
        await log_audit(db, action="permission_denied", user_id=current_user.id,
                        workspace_id=current_user.workspace_id, details=str(e))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return results
