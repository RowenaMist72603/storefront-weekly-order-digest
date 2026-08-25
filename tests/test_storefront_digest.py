from datetime import datetime, timezone

from src.storefront_digest import DigestRequest, build_weekly_digest


def test_digest_sends_completed_orders_and_defers_missing_receipts() -> None:
    request = DigestRequest.model_validate(
        {
            "period_start": "2026-08-10T00:00:00Z",
            "period_end": "2026-08-17T00:00:00Z",
            "orders": [
                {
                    "order_number": "SHOP-1042",
                    "customer_email": "buyer@example.com",
                    "checkout": "completed",
                    "fulfillment": "delivered",
                    "receipt": "sent",
                    "updated_at": "2026-08-12T10:00:00Z",
                },
                {
                    "order_number": "SHOP-1043",
                    "customer_email": "second@example.com",
                    "checkout": "completed",
                    "fulfillment": "shipped",
                    "receipt": "pending",
                    "updated_at": "2026-08-13T10:00:00Z",
                },
            ],
        }
    )

    result = build_weekly_digest(request)

    assert [update.order_number for update in result.updates] == ["SHOP-1042"]
    assert result.updates[0].message == "Order SHOP-1042: delivered"
    assert result.deferred_order_numbers == ["SHOP-1043"]
    assert request.period_start.tzinfo == timezone.utc
