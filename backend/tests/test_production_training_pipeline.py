from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.training.production_disease_pipeline import (
    classification_metrics_from_predictions,
    compute_aecs_from_vectors,
    compute_dtei,
    split_70_15_15,
)


def test_split_70_15_15_preserves_expected_ratios() -> None:
    X = pd.DataFrame({"feature": range(100)})
    y = pd.Series([0, 1] * 50)

    X_train, X_val, X_test, y_train, y_val, y_test = split_70_15_15(X, y)

    assert len(X_train) == 70
    assert len(X_val) == 15
    assert len(X_test) == 15
    assert y_train.nunique() == 2
    assert y_val.nunique() == 2
    assert y_test.nunique() == 2


def test_classification_metrics_include_sensitivity_specificity_auc() -> None:
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 1, 1, 1])
    probabilities = np.array([[0.9, 0.1], [0.4, 0.6], [0.2, 0.8], [0.1, 0.9]])

    metrics = classification_metrics_from_predictions(y_true, y_pred, probabilities)

    assert metrics["accuracy"] == 0.75
    assert metrics["sensitivity"] == 1.0
    assert metrics["specificity"] == 0.5
    assert metrics["roc_auc"] == 1.0
    assert metrics["confusion_matrix"] == [[1, 1], [0, 2]]


def test_trust_and_aecs_are_bounded() -> None:
    assert compute_dtei(1.0, 1.0, 1.0, 1.0, 1.0) == 100.0
    assert compute_dtei(-2.0, 0.0, 0.0, 0.0, 0.0) == 0.0

    aecs_val_1, dist_1 = compute_aecs_from_vectors(np.array([1.0, 0.0]), np.array([1.0, 0.0]))
    assert aecs_val_1 == 1.0
    aecs_val_2, dist_2 = compute_aecs_from_vectors(np.array([1.0, 0.0]), np.array([0.0, 1.0]))
    assert 0.0 <= aecs_val_2 <= 1.0
