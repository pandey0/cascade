"""Loaders for the benchmark datasets (optional `bench` extra; imported lazily)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def load_task(task: str) -> tuple[list[str], NDArray[np.int64], list[str]]:
    """Return (texts, integer gold labels, label names) for ``banking77`` or ``clinc150``.

    banking77: PolyAI/banking77 train+test (CC-BY-4.0 per its HF card).
    clinc150: clinc/clinc_oos "plus", in-scope only (CC-BY-3.0 per its HF card).
    """
    from datasets import concatenate_datasets, load_dataset  # noqa: PLC0415

    if task == "banking77":
        ds = load_dataset("PolyAI/banking77")
        texts = list(ds["train"]["text"]) + list(ds["test"]["text"])
        labels = np.array(list(ds["train"]["label"]) + list(ds["test"]["label"]), dtype=np.int64)
        return texts, labels, list(ds["train"].features["label"].names)
    if task == "clinc150":
        ds = load_dataset("clinc/clinc_oos", "plus")
        names = list(ds["train"].features["intent"].names)
        oos = names.index("oos")
        both = concatenate_datasets([ds["train"], ds["validation"], ds["test"]])
        keep = [i for i, y in enumerate(both["intent"]) if y != oos]
        sub = both.select(keep)
        remap = {old: new for new, old in enumerate(i for i in range(len(names)) if i != oos)}
        labels = np.array([remap[int(y)] for y in sub["intent"]], dtype=np.int64)
        return list(sub["text"]), labels, [n for i, n in enumerate(names) if i != oos]
    msg = f"unknown task: {task}"
    raise ValueError(msg)
