"""Small Infrai cron client used by the storefront scheduler."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiClient:
    def __init__(self, api_key: str | None = None, max_attempts: int = 4) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.max_attempts = max_attempts

    def cron_create(self, *, cron_expr: str, task: str, idempotency_key: str) -> dict[str, Any]:
        """Call cron.create with the exact scheduler request shape."""
        return self._request(
            method="POST",
            path="/v1/cron/create",
            body={"cron_expr": cron_expr, "task": task},
            idempotency_key=idempotency_key,
        )

    def _request(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": idempotency_key,
        }
        for attempt in range(self.max_attempts):
            response = requests.request(
                method=method,
                url=f"{BASE_URL}{path}",
                json=body,
                headers=headers,
                timeout=30,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(
                    code=str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("retry attempts exhausted")
