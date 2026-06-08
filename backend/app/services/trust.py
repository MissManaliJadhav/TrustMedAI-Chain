from dataclasses import dataclass


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


def calculate_dtei(confidence: float, explanation_stability: float, robustness_score: float, blockchain_integrity: float = 0.97, compliance: float = 0.94) -> tuple[float, DTEIComponents]:
    components = DTEIComponents(
        fidelity=round(confidence, 3),
        interpretability=round(explanation_stability, 3),
        robustness=round(robustness_score, 3),
        blockchain_integrity=round(blockchain_integrity, 3),
        compliance=round(compliance, 3),
    )
    dtei = (
        0.30 * components.fidelity
        + 0.20 * components.interpretability
        + 0.20 * components.robustness
        + 0.15 * components.blockchain_integrity
        + 0.15 * components.compliance
    )
    return round(dtei, 3), components
