from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

# Optional: Import cv2 for image support (lazy import in load_images_dataset)
try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
SPLIT_ROOT = PROJECT_ROOT / "data"
ARTIFACT_DIR = PROJECT_ROOT / "backend" / "app" / "ai" / "artifacts"

DATASET_CONFIG = {
    "heart": {
        "target": "num",
        "drop": ["id", "dataset"],
        "binary_positive": lambda v: int(v) > 0,
    },
    "diabetes": {
        "target": "Outcome",
        "drop": [],
        "binary_positive": lambda v: int(v) == 1,
    },
    "asthma": {
        "target": "Severity_None",
        "drop": [],
        "binary_positive": lambda v: int(v) == 1,
    },
    "liver": {
        "target": "Dataset",
        "drop": [],
        "binary_positive": lambda v: int(v) == 2,
    },
    "parkinson": {
        "target": "status",
        "drop": ["name"],
        "binary_positive": lambda v: int(v) == 1,
    },
}

IMAGE_DATASETS = {"pneumonia", "eye", "tuberculosis", "brain_tumor"}


def find_csv_file(raw_dir: Path) -> Path | None:
    csv_files = sorted(raw_dir.glob("*.csv"))
    return csv_files[0] if csv_files else None


def load_dataset(key: str, raw_dir: Path) -> pd.DataFrame | None:
    csv_path = find_csv_file(raw_dir)
    if csv_path is None:
        return None
    return pd.read_csv(csv_path)


def prepare_features(df: pd.DataFrame, key: str) -> tuple[pd.DataFrame, pd.Series] | None:
    config = DATASET_CONFIG[key]
    target_name = config["target"]
    if target_name not in df.columns:
        return None

    df = df.copy()
    df = df.drop(columns=[c for c in config["drop"] if c in df.columns], errors="ignore")
    y = df[target_name].astype(str).fillna("")
    X = df.drop(columns=[target_name], errors="ignore")

    if y.nunique() < 2:
        return None

    if key in DATASET_CONFIG:
        y = y.map(config["binary_positive"]).astype(int)

    X = X.copy()
    for column in X.columns:
        if X[column].dtype == object:
            if X[column].nunique() <= 20:
                X = pd.get_dummies(X, columns=[column], drop_first=True)
            else:
                X[column] = X[column].astype("category").cat.codes

    numeric_cols = X.select_dtypes(include=[np.number]).columns
    X[numeric_cols] = X[numeric_cols].fillna(X[numeric_cols].median())
    for column in X.columns:
        if X[column].dtype == object:
            mode_value = X[column].mode(dropna=True)
            fill_value = mode_value.iloc[0] if not mode_value.empty else ""
            X[column] = X[column].fillna(fill_value)

    if X.shape[1] == 0:
        return None

    return X, y


def load_images_dataset(key: str, raw_dir: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Load images from raw directory and return feature vectors and labels."""
    if cv2 is None:
        print(f"  ⚠ cv2 not available, skipping image dataset for {key}")
        return None
    
    if key not in IMAGE_DATASETS:
        return None
    
    image_dirs = sorted([d for d in raw_dir.iterdir() if d.is_dir()])
    if not image_dirs:
        return None
    
    features_list = []
    labels_list = []
    label_map = {label_dir.name: idx for idx, label_dir in enumerate(image_dirs)}
    
    for label_dir in image_dirs:
        label_idx = label_map[label_dir.name]
        image_files = sorted(label_dir.glob("*.jpg")) + sorted(label_dir.glob("*.png"))
        
        if not image_files:
            continue
        
        for img_path in image_files[:100]:  # Limit to 100 images per class for speed
            try:
                # Load image and resize to 64x64 for memory efficiency
                img = cv2.imread(str(img_path))
                if img is None:
                    continue
                img_resized = cv2.resize(img, (64, 64))
                # Convert to grayscale and flatten
                img_gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
                features = img_gray.flatten().astype(np.float32) / 255.0
                features_list.append(features)
                labels_list.append(label_idx)
            except Exception as e:
                print(f"  Error loading {img_path}: {e}")
                continue
    
    if not features_list:
        return None
    
    X = np.array(features_list)
    y = np.array(labels_list)
    return X, y


def split_and_save(key: str, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray) -> dict[str, Any]:
    """Split data and train model, then save both data and model artifacts."""
    train_dir = SPLIT_ROOT / "train" / key
    val_dir = SPLIT_ROOT / "validation" / key
    test_dir = SPLIT_ROOT / "test" / key
    for folder in (train_dir, val_dir, test_dir):
        folder.mkdir(parents=True, exist_ok=True)

    # Handle both DataFrame and ndarray inputs
    if isinstance(y, np.ndarray):
        stratify = y if len(np.unique(y)) > 1 else None
    else:
        stratify = y if y.nunique() > 1 else None
    
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=stratify
    )
    
    if isinstance(y_temp, np.ndarray):
        stratify_temp = y_temp if len(np.unique(y_temp)) > 1 else None
    else:
        stratify_temp = y_temp if y_temp.nunique() > 1 else None
    
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=stratify_temp
    )

    # Save data splits (convert to CSV for consistency)
    if isinstance(X_train, np.ndarray):
        np.save(train_dir / "features.npy", X_train)
        np.save(val_dir / "features.npy", X_val)
        np.save(test_dir / "features.npy", X_test)
        np.save(train_dir / "labels.npy", y_train)
        np.save(val_dir / "labels.npy", y_val)
        np.save(test_dir / "labels.npy", y_test)
    else:
        pd.concat([X_train, y_train.rename("target")], axis=1).to_csv(train_dir / "data.csv", index=False)
        pd.concat([X_val, y_val.rename("target")], axis=1).to_csv(val_dir / "data.csv", index=False)
        pd.concat([X_test, y_test.rename("target")], axis=1).to_csv(test_dir / "data.csv", index=False)

    model = RandomForestClassifier(n_estimators=80, random_state=42)
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    if isinstance(y, np.ndarray):
        num_classes = len(np.unique(y))
    else:
        num_classes = int(y.nunique())

    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0, average="weighted")),
        "recall": float(recall_score(y_test, predictions, zero_division=0, average="weighted")),
        "f1_score": float(f1_score(y_test, predictions, zero_division=0, average="weighted")),
        "num_classes": int(num_classes),
        "train_rows": int(X_train.shape[0]),
        "validation_rows": int(X_val.shape[0]),
        "test_rows": int(X_test.shape[0]),
    }
    
    # AUC only for binary classification
    if num_classes == 2:
        try:
            probabilities = model.predict_proba(X_test)[:, 1]
            metrics["auc"] = float(roc_auc_score(y_test, probabilities))
        except Exception:
            metrics["auc"] = None

    # Save model to artifacts directory
    model_path = ARTIFACT_DIR / f"{key}_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"✓ Saved model to {model_path}")

    return metrics



def run_all() -> None:
    """Process all datasets: CSV and image-based."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {"datasets": {}, "timestamp": str(Path.cwd())}

    for key in sorted(DATASET_CONFIG.keys()):
        raw_dir = RAW_ROOT / key
        summary["datasets"][key] = {
            "raw_folder": str(raw_dir),
            "data_type": None,
            "data_file": None,
            "status": "skipped",
            "message": None,
            "metrics": None,
        }

        if not raw_dir.exists():
            summary["datasets"][key]["status"] = "missing raw folder"
            continue

        # Try CSV first
        df = load_dataset(key, raw_dir)
        if df is not None:
            summary["datasets"][key]["data_type"] = "csv"
            csv_file = find_csv_file(raw_dir)
            summary["datasets"][key]["data_file"] = str(csv_file.relative_to(PROJECT_ROOT))
            
            result = prepare_features(df, key)
            if result is None:
                summary["datasets"][key]["status"] = "could not prepare csv features"
                continue

            X, y = result
            metrics = split_and_save(key, X, y)
            artifact_path = ARTIFACT_DIR / f"{key}_csv_metrics.json"
            artifact_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

            summary["datasets"][key]["status"] = "completed"
            summary["datasets"][key]["metrics"] = metrics
            print(f"✓ {key}: CSV dataset processed")
            continue

        # Try images if CSV not found
        print(f"→ {key}: CSV not found, trying images...")
        img_result = load_images_dataset(key, raw_dir)
        if img_result is not None:
            summary["datasets"][key]["data_type"] = "images"
            X, y = img_result
            print(f"  Loaded {X.shape[0]} images with shape {X.shape[1:]}")
            
            metrics = split_and_save(key, X, y)
            artifact_path = ARTIFACT_DIR / f"{key}_images_metrics.json"
            artifact_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

            summary["datasets"][key]["status"] = "completed"
            summary["datasets"][key]["metrics"] = metrics
            print(f"✓ {key}: Image dataset processed")
            continue

        summary["datasets"][key]["status"] = "no data found (csv or images)"

    summary_path = PROJECT_ROOT / "data" / "raw_training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n📋 Summary written to {summary_path}")
    print(json.dumps(summary, indent=2))



if __name__ == "__main__":
    run_all()
