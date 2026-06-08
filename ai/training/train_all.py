from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from model_registry import MODEL_REGISTRY

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "backend" / "app" / "ai" / "artifacts"


def synthetic_dataset(seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(512, 16))
    logits = x[:, 0] * 1.1 + x[:, 3] * 0.7 - x[:, 6] * 0.45 + rng.normal(scale=0.4, size=512)
    y = (logits > 0).astype(int)
    return x, y


def train_model(key: str) -> dict[str, float]:
    config = MODEL_REGISTRY[key]
    x, y = synthetic_dataset(abs(hash(key)) % 10000)
    x_train, x_temp, y_train, y_temp = train_test_split(x, y, test_size=0.30, random_state=42, stratify=y)
    x_val, x_test, y_val, y_test = train_test_split(x_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp)

    model = RandomForestClassifier(n_estimators=80, random_state=42)
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, predictions, zero_division=0)), 4),
        "auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        "validation_samples": int(len(x_val)),
        "test_samples": int(len(x_test)),
        "framework_target": config.framework,
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / f"{key}_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=list(MODEL_REGISTRY.keys()) + ["all"], default="all")
    args = parser.parse_args()

    keys = MODEL_REGISTRY.keys() if args.model == "all" else [args.model]
    summary = {key: train_model(key) for key in keys}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
