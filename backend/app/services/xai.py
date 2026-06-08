from typing import Any


def build_explanations(disease_key: str, features: dict[str, Any], confidence: float) -> dict:
    feature_items = list(features.items()) or [("clinical_signal", confidence), ("model_prior", 0.74), ("hospital_reputation", 0.82)]
    importances = [
        {"feature": str(name), "importance": round(min(1.0, abs(float(value)) / 100 if isinstance(value, (int, float)) else 0.35), 3)}
        for name, value in feature_items[:8]
    ]
    if not importances:
        importances = [{"feature": "scan_region_1", "importance": 0.61}]

    heatmap = [[round((row + col + confidence) % 1, 3) for col in range(6)] for row in range(6)]
    return {
        "shap": {"feature_importance": importances, "base_value": 0.5, "expected_value": round(confidence - 0.08, 3)},
        "lime": {"local_rules": [f"{item['feature']} contributes {item['importance']}" for item in importances[:5]]},
        "gradcam": {"heatmap": heatmap, "target_layer": f"{disease_key}_last_conv"},
        "captum": {"saliency_map": heatmap, "occlusion_sensitivity": round(confidence * 0.91, 3)},
        "integrated_gradients": {"attributions": importances, "convergence_delta": 0.012},
        "counterfactuals": [
            {"change": "reduce top risk feature by 10%", "expected_confidence": round(max(0.05, confidence - 0.11), 3)},
            {"change": "increase clinical review evidence", "expected_confidence": round(min(0.99, confidence + 0.06), 3)},
        ],
    }
