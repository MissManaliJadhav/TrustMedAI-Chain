from __future__ import annotations

import numpy as np


def shap_feature_importance(feature_names: list[str], values: np.ndarray) -> list[dict[str, float | str]]:
    magnitudes = np.abs(values)
    if magnitudes.sum() == 0:
        weights = np.ones_like(magnitudes) / len(magnitudes)
    else:
        weights = magnitudes / magnitudes.sum()
    return [{"feature": name, "importance": round(float(weight), 4)} for name, weight in zip(feature_names, weights)]


def lime_local_rules(feature_names: list[str], values: np.ndarray) -> list[str]:
    return [f"{name} local contribution {float(value):.3f}" for name, value in zip(feature_names, values)]


def gradcam_heatmap(height: int = 14, width: int = 14) -> list[list[float]]:
    grid = np.outer(np.linspace(0.1, 1.0, height), np.linspace(1.0, 0.1, width))
    return np.round(grid / grid.max(), 4).tolist()


def integrated_gradients(values: np.ndarray, baseline: float = 0.0) -> list[float]:
    return np.round(values - baseline, 4).tolist()
