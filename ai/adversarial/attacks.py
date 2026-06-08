from __future__ import annotations

import numpy as np


def fgsm(x: np.ndarray, gradient: np.ndarray, epsilon: float = 0.03) -> np.ndarray:
    return x + epsilon * np.sign(gradient)


def pgd(x: np.ndarray, gradient: np.ndarray, epsilon: float = 0.03, steps: int = 8) -> np.ndarray:
    adv = x.copy()
    step_size = epsilon / max(steps, 1)
    for _ in range(steps):
        adv = np.clip(adv + step_size * np.sign(gradient), x - epsilon, x + epsilon)
    return adv


def deepfool_proxy(x: np.ndarray, gradient: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(gradient) + 1e-8
    return x + 0.02 * gradient / norm


def carlini_wagner_proxy(x: np.ndarray, gradient: np.ndarray, confidence: float = 0.1) -> np.ndarray:
    return x + confidence * np.tanh(gradient) * 0.01


def robustness_score(clean_accuracy: float, attacked_accuracy: float, explanation_stability: float) -> float:
    return round(float((clean_accuracy + attacked_accuracy + explanation_stability) / 3), 4)
