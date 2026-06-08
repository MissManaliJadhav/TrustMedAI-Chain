from __future__ import annotations


def dynamic_trust_evolution_index(
    fidelity: float,
    interpretability: float,
    robustness: float,
    blockchain_integrity: float,
    compliance: float,
    alpha: float = 0.30,
    beta: float = 0.20,
    gamma: float = 0.20,
    delta: float = 0.15,
    lam: float = 0.15,
) -> float:
    return round(
        alpha * fidelity
        + beta * interpretability
        + gamma * robustness
        + delta * blockchain_integrity
        + lam * compliance,
        4,
    )


def adversarial_explanation_consistency_score(original: set[int], adversarial: set[int]) -> float:
    if not original and not adversarial:
        return 1.0
    return round(2 * len(original.intersection(adversarial)) / max(1, len(original) + len(adversarial)), 4)
