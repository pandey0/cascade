"""Locust load profile for the gateway (closed loop, held-out Banking77 messages).

Run via scripts/locust_ab.sh. Texts come from data/cache/load_texts.txt (made from the held-out
pool). Anonymous mode must be enabled on the target (CASCADE_ALLOW_ANONYMOUS=1).
"""

from __future__ import annotations

import random
from pathlib import Path

from locust import HttpUser, constant, task

TEXTS = Path("data/cache/load_texts.txt").read_text(encoding="utf-8").splitlines()


class GatewayUser(HttpUser):
    wait_time = constant(0)

    @task
    def decide(self) -> None:
        self.client.post(
            "/v1/decide",
            json={"decision": "banking77", "input": random.choice(TEXTS)},  # noqa: S311
        )
