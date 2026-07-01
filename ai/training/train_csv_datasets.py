from __future__ import annotations

import argparse
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
SPLIT_ROOT = PROJECT_ROOT / "data"
ARTIFACT_DIR = PROJECT_ROOT / "backend" / "app" / "ai" / "artifacts"
RANDOM_STATE = 42

DATASET_CONFIG: dict[str, dict[str, Any]] = {
    "heart": {
        "target": "num",
        "drop": ["id", "dataset"],
        "positive": lambda value: int(value) > 0,
        "class_labels": ["low_risk", "high_risk"],
        "quality_notes": [
            "The UCI source combines cohorts with substantial missingness; imputation is fitted on training data only.",
        ],
    },
    "diabetes": {
        "target": "Outcome",
        "drop": [],
        "positive": lambda value: int(value) == 1,
        "class_labels": ["negative", "positive"],
        "zero_as_missing": ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"],
        "quality_notes": [
            "Physiologically impossible zero measurements are treated as missing and imputed from training data.",
        ],
    },
    "asthma": {
        "target": "Severity_None",
        "drop": ["Severity_Mild", "Severity_Moderate"],
        "positive": lambda value: int(value) == 0,
        "class_labels": ["controlled", "risk"],
        "group_by_features": True,
        "quality_notes": [
            "The source is highly duplicated and appears combinatorial rather than a real patient cohort.",
            "Severity-derived columns are removed because they directly leak the target.",
            "Identical symptom profiles are kept in the same split to prevent near-duplicate leakage.",
        ],
    },
    "liver": {
        "target": "Dataset",
        "drop": [],
        "positive": lambda value: int(value) == 1,
        "class_labels": ["normal", "disease"],
        "quality_notes": [
            "Exact duplicate rows are removed before splitting.",
        ],
    },
    "parkinson": {
        "target": "status",
        "drop": ["name"],
        "positive": lambda value: int(value) == 1,
        "class_labels": ["healthy", "parkinson"],
        "patient_group_column": "name",
        "quality_notes": [
            "Repeated voice recordings from one person are kept in a single split to prevent patient leakage.",
            "This dataset is small, so the held-out estimate has wide uncertainty.",
        ],
    },
}

IMAGE_DATASETS = {"pneumonia", "eye", "tuberculosis", "brain_tumor"}
IMAGE_CLASS_ALIASES = {
    "pneumonia": [("normal", {"normal"}), ("pneumonia", {"pneumonia"})],
    "eye": [
        ("normal", {"normal", "1_normal"}),
        ("cataract", {"cataract", "2_cataract"}),
        ("glaucoma", {"glaucoma", "2_glaucoma"}),
        ("retina", {"retina", "retina_disease", "3_retina_disease"}),
    ],
    "tuberculosis": [("normal", {"normal"}), ("tuberculosis", {"tuberculosis", "tb"})],
    "brain_tumor": [
        ("no_tumor", {"notumor", "no_tumor", "no tumor"}),
        ("glioma", {"glioma"}),
        ("meningioma", {"meningioma"}),
        ("pituitary", {"pituitary"}),
    ],
}


def find_csv_file(raw_dir: Path) -> Path | None:
    files = sorted(raw_dir.glob("*.csv"))
    return files[0] if files else None


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value


def prepare_tabular_dataset(
    key: str, raw_dir: Path
) -> tuple[pd.DataFrame, pd.Series, pd.Series | None, dict[str, Any]] | None:
    path = find_csv_file(raw_dir)
    if path is None:
        return None
    config = DATASET_CONFIG[key]
    source = pd.read_csv(path)
    target = config["target"]
    if target not in source:
        return None

    raw_rows = len(source)
    source = source.drop_duplicates().reset_index(drop=True)
    groups: pd.Series | None = None
    group_column = config.get("patient_group_column")
    if group_column:
        groups = source[group_column].astype(str).str.rsplit("_", n=1).str[0]

    y = source[target].map(config["positive"]).astype(int)
    X = source.drop(columns=[target, *config.get("drop", [])], errors="ignore").copy()
    for column in config.get("zero_as_missing", []):
        if column in X:
            X[column] = pd.to_numeric(X[column], errors="coerce").replace(0, np.nan)

    if config.get("group_by_features"):
        groups = pd.util.hash_pandas_object(X.fillna("<missing>").astype(str), index=False).astype(str)

    if X.empty or y.nunique() < 2:
        return None
    quality = {
        "source_rows": raw_rows,
        "rows_after_exact_deduplication": len(source),
        "exact_duplicates_removed": raw_rows - len(source),
        "feature_count": X.shape[1],
        "class_distribution": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
        "notes": config.get("quality_notes", []),
    }
    return X, y, groups, quality


def _group_split(
    X: pd.DataFrame, y: pd.Series, groups: pd.Series
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    for seed in range(RANDOM_STATE, RANDOM_STATE + 50):
        first = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=seed)
        train_idx, temp_idx = next(first.split(X, y, groups))
        temp_groups = groups.iloc[temp_idx]
        second = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=seed + 100)
        val_rel, test_rel = next(second.split(X.iloc[temp_idx], y.iloc[temp_idx], temp_groups))
        val_idx, test_idx = temp_idx[val_rel], temp_idx[test_rel]
        parts = (y.iloc[train_idx], y.iloc[val_idx], y.iloc[test_idx])
        if all(part.nunique() == y.nunique() for part in parts):
            return (
                X.iloc[train_idx].copy(),
                X.iloc[val_idx].copy(),
                X.iloc[test_idx].copy(),
                parts[0].copy(),
                parts[1].copy(),
                parts[2].copy(),
            )
    raise ValueError("Could not create leakage-safe group splits containing every class.")


def split_tabular(
    X: pd.DataFrame, y: pd.Series, groups: pd.Series | None
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    if groups is not None:
        return _group_split(X, y, groups)
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=RANDOM_STATE, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=RANDOM_STATE, stratify=y_temp
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def build_preprocessor(X: pd.DataFrame) -> tuple[ColumnTransformer, list[str], list[str]]:
    categorical = [
        column
        for column in X.columns
        if not pd.api.types.is_numeric_dtype(X[column]) and not pd.api.types.is_bool_dtype(X[column])
    ]
    numeric = [column for column in X.columns if column not in categorical]
    preprocessor = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categorical,
            ),
        ],
        remainder="drop",
    )
    return preprocessor, numeric, categorical


def candidate_models() -> dict[str, Any]:
    return {
        "logistic_regression": LogisticRegression(
            max_iter=3000, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=350,
            min_samples_leaf=2,
            class_weight="balanced",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=350,
            min_samples_leaf=2,
            class_weight="balanced",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        "neural_network": MLPClassifier(
            hidden_layer_sizes=(64, 24),
            alpha=0.002,
            batch_size=32,
            early_stopping=True,
            validation_fraction=0.15,
            max_iter=350,
            random_state=RANDOM_STATE,
        ),
    }


def calculate_metrics(
    model: Pipeline, X: pd.DataFrame, y: pd.Series, threshold: float = 0.5
) -> dict[str, float]:
    probabilities = model.predict_proba(X)
    prediction = (
        (probabilities[:, 1] >= threshold).astype(int)
        if probabilities.shape[1] == 2
        else np.argmax(probabilities, axis=1)
    )
    result = {
        "accuracy": float(accuracy_score(y, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "precision": float(precision_score(y, prediction, average="weighted", zero_division=0)),
        "recall": float(recall_score(y, prediction, average="weighted", zero_division=0)),
        "f1_score": float(f1_score(y, prediction, average="weighted", zero_division=0)),
    }
    if y.nunique() == 2:
        result["auc"] = float(roc_auc_score(y, probabilities[:, 1]))
        result["sensitivity"] = float(recall_score(y, prediction, pos_label=1, zero_division=0))
        result["specificity"] = float(recall_score(y, prediction, pos_label=0, zero_division=0))
    return result


def choose_threshold(model: Pipeline, X: pd.DataFrame, y: pd.Series) -> float:
    """Select a binary decision threshold on validation data, never on test data."""
    probabilities = model.predict_proba(X)
    if probabilities.shape[1] != 2:
        return 0.5
    candidates = np.unique(np.concatenate(([0.5], np.linspace(0.10, 0.90, 161), probabilities[:, 1])))
    scored = []
    for threshold in candidates:
        prediction = (probabilities[:, 1] >= threshold).astype(int)
        scored.append(
            (
                balanced_accuracy_score(y, prediction),
                f1_score(y, prediction, average="weighted", zero_division=0),
                -abs(float(threshold) - 0.5),
                float(threshold),
            )
        )
    return max(scored)[-1]


def _selection_score(metrics: dict[str, float]) -> float:
    return (
        0.45 * metrics["balanced_accuracy"]
        + 0.35 * metrics["f1_score"]
        + 0.20 * metrics.get("auc", metrics["balanced_accuracy"])
    )


def build_input_schema(
    X_train: pd.DataFrame, numeric: list[str], categorical: list[str]
) -> list[dict[str, Any]]:
    schema: list[dict[str, Any]] = []
    for name in X_train.columns:
        series = X_train[name]
        label = name.replace("_", " ").replace("-", " ").replace(":", " ").strip()
        if name in categorical:
            choices = [_json_value(value) for value in sorted(series.dropna().unique(), key=str)]
            mode = series.mode(dropna=True)
            schema.append(
                {
                    "name": name,
                    "label": label,
                    "input_type": "category",
                    "required": True,
                    "minimum": None,
                    "maximum": None,
                    "default": _json_value(mode.iloc[0]) if not mode.empty else None,
                    "choices": choices,
                }
            )
            continue
        values = pd.to_numeric(series, errors="coerce").dropna()
        unique = set(float(value) for value in values.unique())
        is_boolean = bool(unique) and unique.issubset({0.0, 1.0})
        schema.append(
            {
                "name": name,
                "label": label,
                "input_type": "boolean" if is_boolean else "number",
                "required": True,
                "minimum": float(values.min()) if not values.empty else None,
                "maximum": float(values.max()) if not values.empty else None,
                "default": float(values.median()) if not values.empty else None,
                "choices": None,
            }
        )
    return schema


def save_tabular_splits(
    key: str,
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_val: pd.Series,
    y_test: pd.Series,
) -> None:
    for split, X_part, y_part in [
        ("train", X_train, y_train),
        ("validation", X_val, y_val),
        ("test", X_test, y_test),
    ]:
        folder = SPLIT_ROOT / split / key
        folder.mkdir(parents=True, exist_ok=True)
        output = X_part.copy()
        output["target"] = y_part.to_numpy()
        output.to_csv(folder / "data.csv", index=False)


def train_tabular(key: str, raw_dir: Path) -> dict[str, Any] | None:
    prepared = prepare_tabular_dataset(key, raw_dir)
    if prepared is None:
        return None
    X, y, groups, quality = prepared
    X_train, X_val, X_test, y_train, y_val, y_test = split_tabular(X, y, groups)
    preprocessor, numeric, categorical = build_preprocessor(X_train)

    comparisons: dict[str, dict[str, float]] = {}
    fitted: dict[str, Pipeline] = {}
    thresholds: dict[str, float] = {}
    for name, estimator in candidate_models().items():
        pipeline = Pipeline([("preprocess", preprocessor), ("classifier", estimator)])
        pipeline.fit(X_train, y_train)
        threshold = choose_threshold(pipeline, X_val, y_val)
        metrics = calculate_metrics(pipeline, X_val, y_val, threshold)
        comparisons[name] = {
            **metrics,
            "decision_threshold": threshold,
            "selection_score": _selection_score(metrics),
        }
        fitted[name] = pipeline
        thresholds[name] = threshold
        print(f"  {key}: {name} validation balanced accuracy={metrics['balanced_accuracy']:.3f}")

    selected_name = max(comparisons, key=lambda name: comparisons[name]["selection_score"])
    selected = fitted[selected_name]
    selected_threshold = thresholds[selected_name]
    test_metrics = calculate_metrics(selected, X_test, y_test, selected_threshold)
    test_metrics.update(
        {
            "train_rows": float(len(X_train)),
            "validation_rows": float(len(X_val)),
            "test_rows": float(len(X_test)),
            "num_classes": float(y.nunique()),
        }
    )
    save_tabular_splits(key, X_train, X_val, X_test, y_train, y_val, y_test)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with (ARTIFACT_DIR / f"{key}_model.pkl").open("wb") as handle:
        pickle.dump(selected, handle)
    metadata = {
        "artifact_version": 2,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "modality": "tabular",
        "selected_model": selected_name,
        "decision_threshold": selected_threshold,
        "selection_metric": "0.45 balanced_accuracy + 0.35 weighted_f1 + 0.20 roc_auc",
        "class_labels": DATASET_CONFIG[key]["class_labels"],
        "positive_class": DATASET_CONFIG[key]["class_labels"][1],
        "input_schema": build_input_schema(X_train, numeric, categorical),
        "data_quality": quality,
        "validation_comparison": comparisons,
        "test_metrics": test_metrics,
        "deployment_status": (
            "ready_for_research"
            if test_metrics["balanced_accuracy"] >= 0.60 and test_metrics.get("auc", 1.0) >= 0.60
            else "blocked_low_quality"
        ),
        "limitations": [
            "Research decision-support only; not validated or approved as a medical device.",
            "Performance on this held-out source dataset does not establish clinical generalization.",
        ],
    }
    (ARTIFACT_DIR / f"{key}_model_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    (ARTIFACT_DIR / f"{key}_csv_metrics.json").write_text(
        json.dumps(test_metrics, indent=2), encoding="utf-8"
    )
    return {"metrics": test_metrics, "metadata": metadata}


def load_images_dataset(
    key: str, raw_dir: Path
) -> tuple[np.ndarray, np.ndarray, list[str]] | None:
    """Legacy image baseline loader.

    Image models remain available for application compatibility. Their small,
    flattened-pixel baseline must not be presented as clinically validated DL.
    """
    if cv2 is None:
        return None
    features, labels = [], []
    class_labels = [label for label, _ in IMAGE_CLASS_ALIASES[key]]
    images = [
        path
        for path in raw_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
    for label_index, (_, aliases) in enumerate(IMAGE_CLASS_ALIASES[key]):
        matches = [
            path
            for path in images
            if path.parent.name.lower().replace("-", "_") in aliases
        ][:100]
        for path in matches:
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                continue
            features.append(cv2.resize(image, (64, 64)).reshape(-1).astype(np.float32) / 255.0)
            labels.append(label_index)
    if not features or len(np.unique(labels)) != len(class_labels):
        return None
    return np.asarray(features), np.asarray(labels), class_labels


def train_image_baseline(
    key: str, X: np.ndarray, y: np.ndarray, class_labels: list[str]
) -> dict[str, float]:
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=RANDOM_STATE, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=RANDOM_STATE, stratify=y_temp
    )
    model = RandomForestClassifier(
        n_estimators=300, class_weight="balanced", n_jobs=-1, random_state=RANDOM_STATE
    ).fit(X_train, y_train)
    prediction = model.predict(X_test)
    metrics = {
        "accuracy": float(accuracy_score(y_test, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, prediction)),
        "precision": float(precision_score(y_test, prediction, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_test, prediction, average="weighted", zero_division=0)),
        "f1_score": float(f1_score(y_test, prediction, average="weighted", zero_division=0)),
        "train_rows": float(len(X_train)),
        "validation_rows": float(len(X_val)),
        "test_rows": float(len(X_test)),
        "num_classes": float(len(class_labels)),
    }
    with (ARTIFACT_DIR / f"{key}_model.pkl").open("wb") as handle:
        pickle.dump(model, handle)
    metadata = {
        "artifact_version": 2,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "modality": "image",
        "selected_model": "random_forest_flattened_pixel_baseline",
        "class_labels": class_labels,
        "image_size": [64, 64],
        "test_metrics": metrics,
        "deployment_status": "baseline_only",
        "limitations": [
            "Baseline only: at most 100 images per class and flattened grayscale pixels.",
            "Use patient-level deduplication and transfer-learning CNN validation before clinical claims.",
        ],
    }
    (ARTIFACT_DIR / f"{key}_model_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    (ARTIFACT_DIR / f"{key}_images_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    return metrics


def run_all(selected_keys: set[str] | None = None) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    all_keys = set(DATASET_CONFIG) | IMAGE_DATASETS
    keys = sorted(selected_keys or all_keys)
    summary: dict[str, Any] = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "datasets": {},
    }
    summary_path = PROJECT_ROOT / "data" / "raw_training_summary.json"
    if selected_keys and summary_path.exists():
        try:
            previous = json.loads(summary_path.read_text(encoding="utf-8"))
            if isinstance(previous.get("datasets"), dict):
                summary["datasets"].update(previous["datasets"])
        except (OSError, ValueError):
            pass
    for key in keys:
        if key not in all_keys:
            raise ValueError(f"Unsupported dataset: {key}")
        raw_dir = RAW_ROOT / key
        if not raw_dir.exists():
            summary["datasets"][key] = {"status": "missing_raw_folder"}
            continue
        if key in DATASET_CONFIG:
            result = train_tabular(key, raw_dir)
            summary["datasets"][key] = (
                {"status": "completed", **result}
                if result
                else {"status": "could_not_prepare_tabular_data"}
            )
            continue
        image_data = load_images_dataset(key, raw_dir)
        if image_data is None:
            summary["datasets"][key] = {"status": "no_supported_images_found"}
            continue
        X, y, labels = image_data
        metrics = train_image_baseline(key, X, y, labels)
        summary["datasets"][key] = {"status": "completed_baseline", "metrics": metrics}

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def rebuild_summary_from_artifacts() -> None:
    """Rebuild the project summary without retraining or touching model files."""
    datasets: dict[str, Any] = {}
    for key in sorted(set(DATASET_CONFIG) | IMAGE_DATASETS):
        metadata_path = ARTIFACT_DIR / f"{key}_model_metadata.json"
        metrics_path = ARTIFACT_DIR / (
            f"{key}_csv_metrics.json" if key in DATASET_CONFIG else f"{key}_images_metrics.json"
        )
        if not metadata_path.exists() or not metrics_path.exists():
            datasets[key] = {"status": "missing_artifact"}
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        datasets[key] = {
            "status": metadata.get("deployment_status", "existing_artifact"),
            "modality": metadata.get("modality"),
            "selected_model": metadata.get("selected_model", "legacy_baseline"),
            "trained_at": metadata.get("trained_at"),
            "metrics": json.loads(metrics_path.read_text(encoding="utf-8")),
            "data_quality": metadata.get("data_quality"),
            "limitations": metadata.get("limitations", []),
        }
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "datasets": datasets,
    }
    (PROJECT_ROOT / "data" / "raw_training_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train leakage-resistant TrustMedAI models.")
    parser.add_argument("--model", choices=sorted(set(DATASET_CONFIG) | IMAGE_DATASETS))
    parser.add_argument("--images-only", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    if args.summary_only:
        rebuild_summary_from_artifacts()
    else:
        selection = {args.model} if args.model else (IMAGE_DATASETS if args.images_only else None)
        run_all(selection)
