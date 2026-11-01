# Contributing
1. `python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev,anthropic,gemini]"`.
2. Before a PR: `make check` (ruff, ruff format, mypy --strict, pytest with an 85% coverage gate).
3. Statistical claims need a script, a manifest in `evidence/` and a row in `paper/CLAIMS.md`. Do not tune on evaluation pools.
4. Never commit keys; `.env` is gitignored. Tests must not call paid APIs (inject fakes).
5. Decisions that change behaviour need an ADR in `docs/adr/`.
