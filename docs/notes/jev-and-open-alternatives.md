# Jev: is it open, how to use it, and open alternatives (checked 2026-11-01)

## Is it open source?
- **The model: no, as far as I can verify.** Jev is a hosted service from TypeSafe AI; the vendor homepage says nothing about weights or a licence. A third-party model directory lists it as proprietary with no public weights and restricted commercial use (unverified; read the vendor's Terms of Use at typesafe.ai/legal/terms before relying on it).
- **The SDKs: open.** Python `typesafe-sdk` (PyPI 0.7.5; GitHub typesafe-ai/typesafe-sdk-python, MIT licence per GitHub; PyPI metadata has no licence field) and JavaScript `@typesafe-ai/sdk` (npm 0.7.0, MIT).

## How to use it
1. Create an account at console.typesafe.ai (third-party guide: sign in with Google or an emailed code) and create an API key. I have not created an account for you.
2. `pip install typesafe-sdk`; set `TYPESAFE_API_KEY` in your environment (never commit it).
3. Minimal call (from the SDK README):
```python
from typesafe_sdk import Choice, TypeSafeClient
with TypeSafeClient() as client:
    response = client.system_one(
        state={"document": "I was charged twice. Please fix this ASAP."},
        questions={"category": Choice(instructions="What is this ticket about?",
                                      criteria={"billing": None, "technical": None, "other": None})},
    )
print(response.choices["category"].choice)
```
4. Reported: price about $42 per billion input tokens ($0.042 per million), output free; 64K-token context; typed outputs only (no free text). Free-tier limits, data retention and training-on-inputs policies are **not stated** on the pages I read: check the privacy policy before sending anything non-public. LiteLLM documents a pass-through for TypeSafe.
5. Access status conflicts across sources (early access vs open to everyone since about 20 Sept 2026): check the console.

In this repo: `cascade.backends.JevBackend` wraps only what the README shows (a `Choice` question). Whether per-option probabilities are exposed needs checking in docs.typesafe.ai before building calibration on them.

## Open alternative: SemIf (formerly OpenJev)
- github.com/TheoLeeCJ/SemIf-OpenJev, MIT, created 2026-09-16, independent and **not affiliated** with TypeSafe. It reproduces the *interface pattern* (typed decisions, probabilities read directly from an open model's option scores, no generated text), not Jev's undisclosed model.
- Runs 4B-class open models (e.g., Qwen3.5-4B) on a GPU; a **CPU path via llama.cpp with a GGUF checkpoint**; Apple MLX; a browser WebGPU demo. Includes per-workload temperature calibration.
- For you: no Jev access is fine. Use SemIf-style scoring as the open "System 1" middle tier (E6 in `tracer-analysis.md`); it is also better for a reproducible write-up because it has no API dependency. A 4B model will not fit your 2 GB MX330: use Colab GPU or CPU GGUF for small experiments (measure speed first).

## Decision
Make `DecisionBackend` the stable interface; implement `SemIfBackend` (open, reproducible) first and `JevBackend` as optional. Treat any Jev numbers as vendor-system measurements, never as "your model".
