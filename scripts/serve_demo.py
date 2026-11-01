"""Run the gateway on a real student + real MiniLM embedder with a SIMULATED teacher.

The teacher returns the dataset's gold label after a fixed delay (default 300 ms) so load tests
cost nothing and are reproducible; results must be reported as "simulated teacher latency".
Usage: python scripts/serve_demo.py --port 8081 [--teacher-ms 300] [--torch-threads N]
Env: CASCADE_API_KEYS or CASCADE_ALLOW_ANONYMOUS=1.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "cache" / "hf"))

import uvicorn  # noqa: E402

from cascade.batching import MicroBatcher  # noqa: E402
from cascade.data import two_way_split  # noqa: E402
from cascade.datasets_io import load_task  # noqa: E402
from cascade.engine import Engine, EngineConfig  # noqa: E402
from cascade.gates import select_holm  # noqa: E402
from cascade.gateway.app import Settings, configure_logging, create_app  # noqa: E402
from cascade.store import AuditStore  # noqa: E402
from cascade.students import LogisticStudent  # noqa: E402
from cascade.teacher import TeacherResponse  # noqa: E402

MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8081)
    ap.add_argument("--teacher-ms", type=float, default=300.0)
    ap.add_argument("--torch-threads", type=int, default=0, help="0 = library default")
    ap.add_argument("--batch", type=int, default=0, help="micro-batch size (0 = off)")
    ap.add_argument("--teacher-fail-rate", type=float, default=0.0, help="chaos: random failures")
    ap.add_argument("--teacher-timeout-s", type=float, default=10.0)
    ap.add_argument("--fail-closed", action="store_true", help="503 instead of degraded answers")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--audit-rate", type=float, default=0.02)
    ap.add_argument("--db", default=str(ROOT / "data" / "cache" / "demo_audit.db"))
    args = ap.parse_args()

    import torch  # noqa: PLC0415
    from sentence_transformers import SentenceTransformer  # noqa: PLC0415

    if args.torch_threads:
        torch.set_num_threads(args.torch_threads)
    texts, y, names = load_task("banking77")
    x = np.load(ROOT / "data" / "cache" / "emb_banking77.npy")
    tr, po = two_way_split(texts, 0.5, 0)
    student = LogisticStudent(c=10.0, max_iter=300, seed=0).fit(x[tr], y[tr])
    pred, conf = student.predict_with_confidence(x[po])
    gate = select_holm(conf, (pred != y[po]).astype(np.float64), args.alpha, 0.1)
    print(f"threshold={gate.threshold} coverage={gate.coverage:.3f}", flush=True)
    gold = {t: names[int(v)] for t, v in zip(texts, y, strict=True)}
    encoder = SentenceTransformer(MODEL, device="cpu")

    def embed_many(batch: list[str]) -> np.ndarray:
        return np.asarray(encoder.encode(batch, normalize_embeddings=True), dtype=np.float64)

    if args.batch:
        embed = MicroBatcher(embed_many, max_batch=args.batch, max_wait_s=0.005)
    else:

        def embed(text: str) -> np.ndarray:
            return embed_many([text])[0]

    chaos = np.random.default_rng(0)

    def teacher(text: str) -> TeacherResponse:
        time.sleep(args.teacher_ms / 1000.0)
        if args.teacher_fail_rate and chaos.random() < args.teacher_fail_rate:
            msg = "injected teacher failure"
            raise RuntimeError(msg)
        return TeacherResponse(gold.get(text, names[0]), "simulated", 0, 0, 0.0, args.teacher_ms)

    # Student labels are ints in this demo; map to names for the response.
    class Named:
        def predict_with_confidence(self, xx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            p, c = student.predict_with_confidence(xx)
            return np.array([names[int(i)] for i in p]), c

    store = AuditStore(args.db)
    cfg = EngineConfig(
        decision="banking77",
        alpha=args.alpha,
        audit_rate=args.audit_rate,
        fail_open=not args.fail_closed,
        teacher_timeout_s=args.teacher_timeout_s,
    )
    engine = Engine(cfg, embed, Named(), teacher, store, gate.threshold)
    configure_logging()
    app = create_app({"banking77": engine}, Settings.from_env(), store)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
