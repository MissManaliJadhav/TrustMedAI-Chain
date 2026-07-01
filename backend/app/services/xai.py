from typing import Any


def _unavailable(method: str, reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "method": method,
        "reason": reason,
    }


def build_explanations(disease_key: str, features: dict[str, Any], confidence: float) -> dict:
    """Return an honest capability envelope until model-bound explainers are fitted.

    Previous code generated plausible-looking heatmaps and importances from the
    confidence value. Those values were not SHAP, LIME, Grad-CAM, or Captum
    results and must never be presented as clinical explanations.
    """
    tabular_reason = (
        "No fitted background dataset and model-bound explainer artifact is available "
        f"for the {disease_key} model."
    )
    image_reason = (
        "The current image artifact is a flattened-pixel baseline without a convolutional "
        "layer, so spatial attribution is not available."
    )
    return {
        "shap": _unavailable("SHAP", tabular_reason),
        "lime": _unavailable("LIME", tabular_reason),
        "gradcam": _unavailable("Grad-CAM", image_reason),
        "captum": _unavailable("Captum", image_reason),
        "integrated_gradients": _unavailable("Integrated Gradients", image_reason),
        "counterfactuals": [],
    }
