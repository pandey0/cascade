# 02 Product scope and MVP

## Core concept: a "Decision"
A versioned spec: name, input schema, output type (single label / multi-label / score / yes-no probability), label descriptions, 5-20 examples, teacher model, risk target (e.g., "agree with teacher >= 97% on accepted cheap answers"), budget, escalation policy.

```yaml
decision: ticket_urgency
output: {type: choice, labels: [low, normal, urgent]}
examples: [...]
teacher: {provider: <configurable>, model: <record exact id>}
target: {agreement: 0.97, confidence_level: 0.95}
cheap_path: {backend: embeddings+logreg | fine-tuned-small | jev (optional)}
escalate_to: teacher
shadow_mode: true
```

## MVP (v0.1: what a small team would need to run it)
1. **Decision builder** (YAML + small web UI): define labels/examples; run teacher on a sample; show label distribution and disagreement.
2. **Cheap model training** from teacher labels (embeddings + classifier first; optional small fine-tune; optional Jev backend); reproducible, versioned.
3. **Calibration + policy:** temperature scaling or conformal calibration; choose confidence threshold to meet the target; report expected coverage (cheap share) and cost.
4. **Gateway/SDK:** `POST /decide` and an OpenAI-compatible endpoint for drop-in use; Python and TypeScript SDKs.
5. **Shadow mode:** run cascade alongside the existing LLM call, compare, never serve until approved.
6. **Dashboard:** cost per 1,000 decisions (before/after), latency p50/p95, % escalated, agreement with teacher on audit samples, calibration plot, drift alerts.
7. **Review queue:** low-confidence or disputed items for human labelling; labels join the training set.
8. **Audit log + rollback:** every decision logged with model/version/confidence; one-click revert to teacher-only.

## Not in v0.1
Generative tasks (summaries, chat), fine-tuning marketplace, on-prem install, SOC2, billing automation (manual invoices first), multi-region.

## Example user stories (drive the API and UI design)
- "As a support lead I see how many tickets can be triaged by the cheap path with 97% agreement, before changing anything."
- "As a developer I swap one base URL and keep my prompts."
- "As an owner I get an alert when the cheap model's agreement drops."
