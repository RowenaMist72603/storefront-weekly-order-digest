"""Typed storefront lifecycle models and the weekly digest decision."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from fastapi import FastAPI
from pydantic import BaseModel, Field


class CheckoutState(str, Enum):
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class FulfillmentState(str, Enum):
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class ReceiptState(str, Enum):
    PENDING = "pending"
    SENT = "sent"


class OrderUpdate(BaseModel):
    order_number: str
    customer_email: str
    checkout: CheckoutState
    fulfillment: FulfillmentState
    receipt: ReceiptState
    updated_at: datetime


class DigestRequest(BaseModel):
    period_start: datetime
    period_end: datetime
    orders: list[OrderUpdate] = Field(default_factory=list)


class CustomerOrderUpdate(BaseModel):
    order_number: str
    customer_email: str
    message: str


class DigestResponse(BaseModel):
    updates: list[CustomerOrderUpdate]
    deferred_order_numbers: list[str]


def build_weekly_digest(request: DigestRequest) -> DigestResponse:
    updates: list[CustomerOrderUpdate] = []
    deferred: list[str] = []
    for order in request.orders:
        in_period = request.period_start <= order.updated_at < request.period_end
        if not in_period or order.checkout != CheckoutState.COMPLETED:
            continue
        if order.receipt != ReceiptState.SENT:
            deferred.append(order.order_number)
            continue
        updates.append(
            CustomerOrderUpdate(
                order_number=order.order_number,
                customer_email=order.customer_email,
                message=f"Order {order.order_number}: {order.fulfillment.value}",
            )
        )
    return DigestResponse(updates=updates, deferred_order_numbers=deferred)


app = FastAPI(title="Storefront weekly digest")


@app.post("/weekly-digest", response_model=DigestResponse)
def weekly_digest(request: DigestRequest) -> DigestResponse:
    return build_weekly_digest(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready", "checked_at": datetime.now(timezone.utc).isoformat()}
