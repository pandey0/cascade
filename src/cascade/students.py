"""Cheap models: frozen-embedding classifiers with optional temperature scaling."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize_scalar
from scipy.special import log_softmax, softmax
from sklearn.linear_model import LogisticRegression

FloatArray = NDArray[np.float64]


class LogisticStudent:
    """Logistic regression on precomputed embeddings; confidence = max class probability."""

    def __init__(self, c: float = 10.0, max_iter: int = 1000, seed: int = 0) -> None:
        self._clf = LogisticRegression(C=c, max_iter=max_iter, random_state=seed)
        self.temperature = 1.0

    def fit(self, x: FloatArray, y: NDArray[np.str_] | list[str]) -> LogisticStudent:
        self._clf.fit(x, y)
        return self

    @property
    def classes_(self) -> NDArray[np.str_]:
        return np.asarray(self._clf.classes_)

    def logits(self, x: FloatArray) -> FloatArray:
        z = np.asarray(self._clf.decision_function(x), dtype=np.float64)
        if z.ndim == 1:  # binary case: sklearn returns one logit; expand to two columns
            z = np.stack([-z / 2.0, z / 2.0], axis=1)
        return z

    def calibrate(self, x: FloatArray, y: NDArray[np.str_] | list[str]) -> float:
        """Fit a single temperature on a held-out calibration set by minimising NLL."""
        z = self.logits(x)
        idx = np.searchsorted(self.classes_, np.asarray(y))

        def nll(t: float) -> float:
            return -float(np.mean(log_softmax(z / t, axis=1)[np.arange(len(idx)), idx]))

        # scipy-stubs overload resolution rejects this valid bounded call
        result = minimize_scalar(nll, bounds=(0.05, 20.0), method="bounded")  # type: ignore[call-overload]
        self.temperature = float(result.x)
        return self.temperature

    def predict_with_confidence(self, x: FloatArray) -> tuple[NDArray[np.str_], FloatArray]:
        p = softmax(self.logits(x) / self.temperature, axis=1)
        return self.classes_[np.argmax(p, axis=1)], p.max(axis=1)


def save_student(student: LogisticStudent, path: str) -> None:
    """Persist a fitted student as plain arrays (no pickle: loading never executes code)."""
    clf = student._clf
    np.savez(
        path,
        coef=clf.coef_,
        intercept=clf.intercept_,
        classes=np.asarray(clf.classes_).astype(str),
        temperature=np.array(student.temperature),
    )


def load_student(path: str) -> LogisticStudent:
    data = np.load(path, allow_pickle=False)
    student = LogisticStudent()
    clf = student._clf
    clf.coef_ = data["coef"]
    clf.intercept_ = data["intercept"]
    clf.classes_ = data["classes"]
    clf.n_features_in_ = data["coef"].shape[1]
    student.temperature = float(data["temperature"])
    return student
