from app.services.adversarial import dice_similarity
from app.services.trust import calculate_dtei


def test_dtei_bounds() -> None:
    value, components = calculate_dtei(0.9, 0.8, 0.7, 0.95, 0.93)
    assert 0 <= value <= 1
    assert components.fidelity == 0.9


def test_aecs_dice() -> None:
    assert dice_similarity([0.5, 0.1, 0.7], [0.4, 0.2, 0.8]) == 1.0
