# 06 Risks and ethics
| Risk | Mitigation |
|---|---|
| Provider terms may restrict using LLM outputs to train other models | read each provider's current terms; use permitted teachers or open-weight models where unclear; document the choice |
| Customer or personal data sent to third-party APIs | demo with public/synthetic data only; PII redaction option; never send employer/client data |
| Over-claiming guarantees | state assumptions (exchangeability, audit sampling); auto-fallback; publish failure cases |
| Jev proprietary/new, terms and access unclear | optional backend only; pin versions; keep a fallback |
| High-stakes decisions (hiring, credit, safety) | do not showcase automated rejection; require human review in any such demo |
| Secrets in repos/logs | secret scanning in CI; redaction; never commit env files |
| Employer/client IP | personal time and equipment; no employer or client code/data |
| Name clash | pick a distinctive name before publishing |
| Scope creep | technical gates in `07`; stopping after Phase 3 still yields a complete system |
