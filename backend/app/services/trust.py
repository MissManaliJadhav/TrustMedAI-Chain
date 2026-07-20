from dataclasses import dataclass


DTEI_WEIGHTS = {
    "fidelity": 0.30,
    "interpretability": 0.20,
    "robustness": 0.20,
    "blockchain_integrity": 0.15,
    "compliance": 0.15,
}


@dataclass(frozen=True)
class DTEIComponents:
    fidelity: float
    interpretability: float
    robustness: float
    blockchain_integrity: float
    compliance: float

    def as_dict(self) -> dict[str, float]:
        return {
            "fidelity": self.fidelity,
            "interpretability": self.interpretability,
            "robustness": self.robustness,
            "blockchain_integrity": self.blockchain_integrity,
            "compliance": self.compliance,
        }


def _normalize_score(value: float | int | None) -> float:
    if value is None:
        return 0.0
    score = float(value)
    if score > 1.0:
        score = score / 100.0
    return round(min(1.0, max(0.0, score)), 3)


def _validated_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    selected = weights or DTEI_WEIGHTS
    required = set(DTEI_WEIGHTS)
    if set(selected) != required:
        missing = sorted(required - set(selected))
        extra = sorted(set(selected) - required)
        raise ValueError(f"DTEI weights must contain exactly {sorted(required)}; missing={missing}, extra={extra}")
    total = sum(float(value) for value in selected.values())
    if abs(total - 1.0) > 0.0001:
        raise ValueError(f"DTEI weights must sum to 1.0, got {total:.4f}")
    return {key: float(value) for key, value in selected.items()}


def dtei_status(score: float) -> str:
    normalized = _normalize_score(score)
    if normalized >= 0.80:
        return "High Trust"
    if normalized >= 0.60:
        return "Moderate Trust"
    if normalized >= 0.40:
        return "Low Trust"
    return "Critical Review Required"


def calculate_dtei(
    confidence: float,
    explanation_stability: float,
    robustness_score: float,
    blockchain_integrity: float = 0.0,
    compliance: float = 0.0,
    *,
    weights: dict[str, float] | None = None,
) -> tuple[float, DTEIComponents]:
    selected_weights = _validated_weights(weights)
    components = DTEIComponents(
        fidelity=_normalize_score(confidence),
        interpretability=_normalize_score(explanation_stability),
        robustness=_normalize_score(robustness_score),
        blockchain_integrity=_normalize_score(blockchain_integrity),
        compliance=_normalize_score(compliance),
    )
    dtei = (
        selected_weights["fidelity"] * components.fidelity
        + selected_weights["interpretability"] * components.interpretability
        + selected_weights["robustness"] * components.robustness
        + selected_weights["blockchain_integrity"] * components.blockchain_integrity
        + selected_weights["compliance"] * components.compliance
    )
    return round(dtei, 3), components
