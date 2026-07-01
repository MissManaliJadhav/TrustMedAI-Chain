def evaluate_attacks(confidence: float) -> dict[str, float]:
    """Return a conservative result when no real attack suite has been run.

    Robustness cannot be inferred from one prediction's confidence.
    """
    return {
        "evaluated": 0.0,
        "fgsm_accuracy": 0.0,
        "pgd_accuracy": 0.0,
        "deepfool_accuracy": 0.0,
        "cw_accuracy": 0.0,
        "attack_accuracy": 0.0,
        "defense_accuracy": 0.0,
        "robustness_score": 0.0,
        "explanation_stability": 0.0,
    }


def dice_similarity(original: list[float], adversarial: list[float]) -> float:
    original_set = {idx for idx, value in enumerate(original) if value > 0.25}
    adversarial_set = {idx for idx, value in enumerate(adversarial) if value > 0.25}
    if not original_set and not adversarial_set:
        return 1.0
    return round(2 * len(original_set & adversarial_set) / max(1, len(original_set) + len(adversarial_set)), 3)


def calculate_aecs(confidence: float) -> float:
    # AECS requires real original/adversarial attribution maps.
    return 0.0
