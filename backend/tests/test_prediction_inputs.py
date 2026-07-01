import pytest

from app.services.prediction import PredictionInputError, _tabular_prediction, get_feature_schema


@pytest.mark.parametrize(
    ("disease_key", "expected_count"),
    [
        ("heart", 13),
        ("diabetes", 8),
        ("asthma", 16),
        ("liver", 10),
        ("parkinson", 22),
    ],
)
def test_feature_schema_matches_trained_model(disease_key: str, expected_count: int) -> None:
    schema = get_feature_schema(disease_key)
    assert len(schema) == expected_count
    assert all(feature["required"] for feature in schema)


def test_prediction_rejects_incomplete_feature_set() -> None:
    with pytest.raises(PredictionInputError, match="Missing required features"):
        _tabular_prediction({"Age": 50}, "diabetes")


def test_prediction_accepts_complete_model_schema() -> None:
    schema = get_feature_schema("diabetes")
    features = {feature["name"]: feature["default"] for feature in schema}
    model_class, confidence, normalized = _tabular_prediction(features, "diabetes")

    assert model_class in {0, 1}
    assert 0 <= confidence <= 1
    assert list(normalized) == [feature["name"] for feature in schema]


def test_prediction_accepts_clinician_facing_categorical_values() -> None:
    schema = get_feature_schema("heart")
    features = {feature["name"]: feature["default"] for feature in schema}
    features["sex"] = "Female"
    features["cp"] = "atypical angina"

    model_class, confidence, normalized = _tabular_prediction(features, "heart")

    assert model_class in {0, 1}
    assert 0 <= confidence <= 1
    assert normalized["sex"] == "Female"


def test_prediction_rejects_unknown_category() -> None:
    schema = get_feature_schema("heart")
    features = {feature["name"]: feature["default"] for feature in schema}
    features["cp"] = "not-a-real-category"

    with pytest.raises(PredictionInputError, match="cp must be one of"):
        _tabular_prediction(features, "heart")


def test_prediction_rejects_out_of_range_values() -> None:
    schema = get_feature_schema("diabetes")
    features = {feature["name"]: feature["default"] for feature in schema}
    features["Glucose"] = 1000

    with pytest.raises(PredictionInputError, match="Glucose must be at most"):
        _tabular_prediction(features, "diabetes")
