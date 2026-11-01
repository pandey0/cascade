"""Pluggable cheap/fast decision backends (the "System 1" slot).

A backend answers a closed-set decision. Only the pieces verified against the vendor's public
SDK README are implemented for Jev (``Choice`` question, ``.choices[name].choice``). Whether and
how per-option probabilities are exposed must be checked in the official docs before use.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class DecisionBackend(Protocol):
    name: str

    def choose(self, text: str, labels: Sequence[str], instructions: str) -> str:
        """Return exactly one label from ``labels``."""
        ...


class JevBackend:
    """Adapter for TypeSafe's hosted Jev model (proprietary service, MIT-licensed SDK).

    Requires ``pip install typesafe-sdk`` and ``TYPESAFE_API_KEY`` in the environment.
    A client can be injected for tests.
    """

    name = "jev"

    def __init__(self, client: Any | None = None) -> None:
        if client is None:
            from typesafe_sdk import TypeSafeClient  # noqa: PLC0415  (optional dependency)

            client = TypeSafeClient()
        self._client = client

    def choose(self, text: str, labels: Sequence[str], instructions: str) -> str:
        from typesafe_sdk import Choice  # noqa: PLC0415  (optional dependency)

        response = self._client.system_one(
            state={"document": text},
            questions={
                "decision": Choice(instructions=instructions, criteria=dict.fromkeys(labels))
            },
        )
        label = str(response.choices["decision"].choice)
        if label not in labels:
            msg = f"backend returned a label outside the closed set: {label!r}"
            raise ValueError(msg)
        return label
