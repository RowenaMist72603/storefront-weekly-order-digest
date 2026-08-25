"""Register the deployed storefront digest route on a weekly schedule."""

import os

from src.infrai_client import InfraiClient


def schedule_weekly_digest() -> str:
    task_url = os.environ["DIGEST_TASK_URL"]
    result = InfraiClient().cron_create(
        cron_expr="0 9 * * 1",
        task=task_url,
        idempotency_key="storefront-weekly-digest-v1",
    )
    return str(result["job_id"])


if __name__ == "__main__":
    print(f"Scheduled storefront digest: {schedule_weekly_digest()}")
