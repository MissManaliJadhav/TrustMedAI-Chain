from typing import Any
import numpy as np


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



def compute_aecs_from_vectors(original: Any, attacked: Any, *, epsilon: float = 1e-12) -> tuple[float, float]:
    """Compute normalized AECS from two numeric vectors.

    Returns a float in the range [0.0, 1.0]. If vectors are empty or invalid,
    raises ValueError.
    """
    orig = np.asarray(original, dtype=float).ravel()
    att = np.asarray(attacked, dtype=float).ravel()
    if orig.size == 0 or att.size == 0:
        raise ValueError("Empty explanation vectors")
    # Align lengths
    n = min(orig.size, att.size)
    orig = orig[:n]
    att = att[:n]
    # Compute Euclidean distance
    distance = float(np.linalg.norm(orig - att))
    denom = float(np.linalg.norm(orig)) + float(epsilon)
    similarity_pct = max(0.0, min(100.0, (1.0 - distance / denom) * 100.0))
    return float(round(similarity_pct / 100.0, 4)), float(distance)


def calculate_aecs(
    confidence: float,
    *,
    explanation: dict[str, Any] | None = None,
    adversarial: dict[str, Any] | None = None,
    patient_attack: dict[str, Any] | None = None,
) -> tuple[float | None, str | None, float | None]:
    """Try to compute a dynamic AECS for the current diagnosis.

    Returns a tuple `(aecs, reason, distance)` where `aecs` is a float in [0,1]
    when computed, otherwise `None` and `reason` explains why it could not
    be computed. `distance` is the Euclidean distance between explanation vectors,
    when AECS is successfully computed.
    """
    try:
        # Only proceed if we have feature values to compare
        if not isinstance(patient_attack, dict):
            return None, "No attack data available for AECS computation.", None

        orig_vals = patient_attack.get("original_values")
        adv_vals = patient_attack.get("adversarial_values")
        if not isinstance(orig_vals, dict) or not isinstance(adv_vals, dict):
            return None, "Original and adversarial feature values are not available.", None

        # Extract numeric values from both feature dicts in aligned order
        try:
            feature_names = sorted(set(orig_vals.keys()) & set(adv_vals.keys()))
            if not feature_names:
                return None, "No common features found between original and adversarial data.", None

            orig_vec = np.asarray([float(orig_vals[k]) for k in feature_names], dtype=float)
            adv_vec = np.asarray([float(adv_vals[k]) for k in feature_names], dtype=float)
        except (TypeError, ValueError) as e:
            return None, f"Could not extract numeric feature values: {e}", None

        # Try to weight by feature importance if available
        fi_weights = None
        if isinstance(explanation, dict):
            shap_info = explanation.get("shap")
            if isinstance(shap_info, dict):
                fi_raw = shap_info.get("feature_importance")
                if isinstance(fi_raw, list) and fi_raw:
                    # feature_importance might be floats or dicts with importance values
                    fi_values = []
                    for item in fi_raw:
                        if isinstance(item, (int, float)):
                            fi_values.append(float(item))
                        elif isinstance(item, dict) and "importance" in item:
                            fi_values.append(float(item["importance"]))
                        elif isinstance(item, dict) and "value" in item:
                            fi_values.append(float(item["value"]))
                    if fi_values:
                        fi_weights = np.asarray(fi_values[:len(feature_names)], dtype=float)

        # Build explanation vectors
        if fi_weights is not None and len(fi_weights) == len(orig_vec):
            # Weight feature values by importance
            e_before = fi_weights * orig_vec
            e_after = fi_weights * adv_vec
        else:
            # Use feature values directly
            e_before = orig_vec
            e_after = adv_vec

        # Compute AECS from the vectors
        aecs_val, dist = compute_aecs_from_vectors(e_before, e_after)
        return aecs_val, None, dist

    except Exception as exc:
        return None, f"AECS computation error: {exc}", None
