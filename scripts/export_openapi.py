"""Write the gateway's OpenAPI spec to docs/openapi.json (generated; do not edit by hand)."""

from __future__ import annotations

import json
from pathlib import Path

from cascade.gateway.app import create_app

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "docs" / "openapi.json").write_text(
    json.dumps(create_app().openapi(), indent=2), encoding="utf-8"
)
print("wrote docs/openapi.json")
