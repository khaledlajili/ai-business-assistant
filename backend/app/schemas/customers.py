from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal
from typing import Optional


class CustomerSearchResult(BaseModel):
    id: UUID
    name: str


class RecentOrder(BaseModel):
    id: str
    status: str
    total_amount: Decimal
    ordered_at: str


class CustomerSummary(BaseModel):
    customer_id: UUID
    name: str
    total_spent: Decimal
    order_count: int
    recent_orders: list[RecentOrder]


class SalesSummary(BaseModel):
    total_amount: Decimal
    order_count: int
    period_start: str
    period_end: str


class InactiveHighValueCustomer(BaseModel):
    customer_id: UUID
    name: str
    email: str
    previous_month_spend: Decimal
