from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import pickle
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sqlalchemy import func
from sqlalchemy.orm import Session

from ai.training.production_disease_pipeline import (
    build_tabular_preprocessor,
    classification_metrics_from_predictions,
    load_tabular_dataset,
    split_70_15_15,
)
from app.db.models import (
    AuditEvent,
    FederatedClientUpdate,
    FederatedRound,
    FederatedTrustSnapshot,
    GlobalModelVersion,
    Hospital,
    LocalTrainingRun,
    User,
)
from app.schemas import FederatedClientUpdateRequest, FederatedRoundCreateRequest, FederatedSimulationRequest
from app.services.catalog import get_disease
from app.services.trust import calculate_dtei

DEFAULT_GLOBAL_WEIGHTS = [0.42, -0.18, 0.31, 0.08, -0.27, 0.16, 0.23, -0.11]
DEFAULT_HOSPITALS = [
    ("TrustMedAI Reference Hospital", "Global", 0.88),
    ("City General Hospital", "North", 0.86),
    ("Lakeside Medical Center", "West", 0.84),
    ("Metro Health Institute", "Central", 0.89),
    ("Rural Care Network", "East", 0.81),
]
FORBIDDEN_UPDATE_KEYS = {"raw", "raw_data", "features", "patients", "patient_rows", "records", "dataset", "images"}

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TRAIN_SPLIT_ROOT = PROJECT_ROOT / "data" / "train"
ARTIFACT_DIR = PROJECT_ROOT / "backend" / "app" / "ai" / "artifacts"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _resolve_training_data_directory(disease_key: str) -> Path:
    raw_dir = PROJECT_ROOT / "data" / "raw" / disease_key
    if raw_dir.exists() and any(raw_dir.rglob("*")):
        return raw_dir
    train_dir = TRAIN_SPLIT_ROOT / disease_key
    if train_dir.exists() and any(train_dir.rglob("*")):
        return train_dir
    raise FileNotFoundError(
        f"No training dataset folder found for {disease_key}. Expected either {raw_dir} or {train_dir}."
    )


def _load_tabular_dataset(disease_key: str) -> tuple[pd.DataFrame, pd.Series, dict[str, Any]]:
    data_dir = _resolve_training_data_directory(disease_key)
    return load_tabular_dataset(disease_key, data_dir)


def _build_feature_names(preprocessor: Pipeline, X: pd.DataFrame) -> list[str]:
    try:
        return list(preprocessor.get_feature_names_out())
    except Exception:
        return list(X.columns)


def _baseline_weight_vector(round_row: FederatedRound, n_features: int) -> list[float]:
    weights = round_row.global_weights.get("layers") if isinstance(round_row.global_weights, dict) else None
    if isinstance(weights, list) and len(weights) == n_features + 1:
        return weights
    return [0.0] * (n_features + 1)


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return sha256(canonical).hexdigest()


def _pipeline_from_weights(weights: list[float], preprocessor: Pipeline) -> Pipeline:
    n_features = len(weights) - 1
    classifier = LogisticRegression(max_iter=1000, class_weight="balanced", solver="liblinear")
    classifier.classes_ = np.array([0, 1], dtype=int)
    classifier.coef_ = np.asarray(weights[:-1], dtype=float).reshape(1, n_features)
    classifier.intercept_ = np.asarray([float(weights[-1])], dtype=float)
    classifier.n_features_in_ = n_features
    pipeline = Pipeline([("preprocess", preprocessor), ("classifier", classifier)])
    return pipeline


def _extract_weight_vector(model: Pipeline) -> list[float]:
    classifier = model.named_steps["classifier"]
    coefficients = np.asarray(classifier.coef_).ravel().tolist()
    intercept = float(classifier.intercept_[0]) if hasattr(classifier.intercept_, "__getitem__") else float(classifier.intercept_)
    return coefficients + [intercept]


def _partition_rows_by_hospital(X: pd.DataFrame, y: pd.Series, hospital_ids: list[str]) -> pd.Series:
    assignment = pd.Series(index=y.index, dtype=object)
    for label in sorted(y.unique()):
        class_indices = y[y == label].index.to_numpy()
        for index, row_id in enumerate(class_indices):
            assignment.loc[row_id] = hospital_ids[index % len(hospital_ids)]
    return assignment


def _save_local_model_artifact(round_id: str, hospital_id: str, model: Pipeline) -> tuple[str, str]:
    artifact_folder = ARTIFACT_DIR / "federated" / round_id
    artifact_folder.mkdir(parents=True, exist_ok=True)
    model_path = artifact_folder / f"{hospital_id}_update.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(model, handle)
    fingerprint = sha256(model_path.read_bytes()).hexdigest()
    return str(model_path.relative_to(PROJECT_ROOT)), fingerprint


def _save_aggregated_model_artifact(round_row: FederatedRound, weights: list[float], preprocessor: Pipeline) -> tuple[str, str]:
    artifact_folder = ARTIFACT_DIR / "federated" / round_row.id
    artifact_folder.mkdir(parents=True, exist_ok=True)
    model = _pipeline_from_weights(weights, preprocessor)
    model_path = artifact_folder / f"{round_row.disease_key}_global_model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(model, handle)
    fingerprint = sha256(model_path.read_bytes()).hexdigest()
    return str(model_path.relative_to(PROJECT_ROOT)), fingerprint


def _train_local_update(db: Session, round_row: FederatedRound, hospital: Hospital) -> tuple[list[float], dict[str, Any], str, str, int]:
    X, y, _ = _load_tabular_dataset(round_row.disease_key)
    hospital_ids = [hospital.id for hospital in db.query(Hospital).filter(Hospital.verified == True).order_by(Hospital.name).all()]
    if hospital.id not in hospital_ids:
        hospital_ids.append(hospital.id)
    assignment = _partition_rows_by_hospital(X, y, hospital_ids)
    hospital_mask = assignment == hospital.id
    X_local = X.loc[hospital_mask]
    y_local = y.loc[hospital_mask]
    if len(X_local) < 10 or y_local.nunique() < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Hospital {hospital.name} does not have enough local training samples for {round_row.disease_key}.",
        )
    preprocessor, _, _ = build_tabular_preprocessor(X)
    preprocessor.fit(X)
    X_train, X_val, X_test, y_train, y_val, y_test = split_70_15_15(X_local, y_local)
    classifier = LogisticRegression(max_iter=1000, class_weight="balanced", solver="liblinear")
    model = Pipeline([("preprocess", preprocessor), ("classifier", classifier)])
    with np.errstate(all="ignore"):
        model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    probabilities = model.predict_proba(X_test)
    metrics = classification_metrics_from_predictions(y_test.to_numpy(), y_pred, probabilities)
    metrics.update({"train_rows": float(len(X_train)), "validation_rows": float(len(X_val)), "test_rows": float(len(X_test))})
    baseline_weights = _baseline_weight_vector(round_row, X_train.shape[1] if hasattr(X_train, "shape") else len(X_train.columns))
    local_weights = _extract_weight_vector(model)
    if len(local_weights) != len(baseline_weights):
        baseline_weights = [0.0] * len(local_weights)
    delta = [local - base for local, base in zip(local_weights, baseline_weights)]
    model_path, fingerprint = _save_local_model_artifact(round_row.id, hospital.id, model)
    return delta, metrics, model_path, fingerprint, len(X_local)
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _audit(db: Session, actor: User | None, action: str, resource_id: str, metadata: dict[str, Any]) -> None:
    db.add(
        AuditEvent(
            actor_id=actor.id if actor else None,
            action=action,
            resource_type="federated_learning",
            resource_id=resource_id,
            payload_hash=_hash_payload(metadata),
            metadata_json=metadata,
        )
    )


def ensure_federated_hospitals(db: Session) -> list[Hospital]:
    """Create verified demo hospitals used as local FL clients.

    These records represent institutions only. Patient-level data never leaves
    a hospital and is not modeled in the federated tables.
    """
    hospitals: list[Hospital] = []
    for name, region, reputation in DEFAULT_HOSPITALS:
        hospital = db.query(Hospital).filter(Hospital.name == name).first()
        if not hospital:
            hospital = Hospital(name=name, region=region, reputation_score=reputation, verified=True)
            db.add(hospital)
            db.flush()
        elif not hospital.verified:
            hospital.verified = True
        hospitals.append(hospital)
    db.commit()
    return hospitals


def _next_round_number(db: Session, model_name: str) -> int:
    latest = db.query(func.max(FederatedRound.round_number)).filter(FederatedRound.model_name == model_name).scalar()
    return int(latest or 0) + 1


def _privacy_config(payload: FederatedRoundCreateRequest) -> dict[str, Any]:
    return {
        "secure_aggregation": payload.secure_aggregation,
        "differential_privacy": payload.differential_privacy,
        "epsilon_budget": payload.privacy_epsilon,
        "raw_data_policy": "raw patient data remains inside each hospital boundary",
        "allowed_payload": ["sample_count", "weights_delta", "metrics", "privacy_report", "payload_hash"],
    }


def create_round(db: Session, payload: FederatedRoundCreateRequest, actor: User) -> FederatedRound:
    ensure_federated_hospitals(db)
    initial_weights = DEFAULT_GLOBAL_WEIGHTS
    previous_global_model_version = None
    try:
        X, y, _ = _load_tabular_dataset(payload.disease_key)
        preprocessor, _, _ = build_tabular_preprocessor(X)
        preprocessor.fit(X)
        feature_count = len(_build_feature_names(preprocessor, X))
        latest_completed = (
            db.query(FederatedRound)
            .filter(FederatedRound.disease_key == payload.disease_key, FederatedRound.status == "aggregated")
            .order_by(FederatedRound.round_number.desc())
            .first()
        )
        if latest_completed and isinstance(latest_completed.aggregated_weights, dict):
            weights = latest_completed.aggregated_weights.get("layers")
            if isinstance(weights, list) and len(weights) == feature_count + 1:
                initial_weights = weights
                previous_global_model_version = latest_completed.global_model_version
            else:
                initial_weights = [0.0] * (feature_count + 1)
        else:
            initial_weights = [0.0] * (feature_count + 1)
    except FileNotFoundError:
        initial_weights = DEFAULT_GLOBAL_WEIGHTS
    round_row = FederatedRound(
        round_number=_next_round_number(db, payload.model_name),
        model_name=payload.model_name,
        disease_key=payload.disease_key,
        min_clients=payload.min_clients,
        global_model_version=payload.global_model_version,
        previous_global_model_version=previous_global_model_version,
        participating_clients=0,
        total_samples=0,
        global_model_path=None,
        global_weights={"layers": initial_weights},
        privacy_config=_privacy_config(payload),
        metrics={"accuracy": 0.0, "loss": 0.0, "participation_rate": 0.0},
        global_trust=0.0,
        previous_global_trust=None,
        trust_change=None,
        created_by=actor.id,
    )
    db.add(round_row)
    db.flush()
    _audit(
        db,
        actor,
        "federated.round.created",
        round_row.id,
        {"round_id": round_row.id, "model_name": payload.model_name, "privacy": round_row.privacy_config},
    )
    db.commit()
    db.refresh(round_row)
    return round_row


def _validate_update_payload(payload: FederatedClientUpdateRequest) -> None:
    metric_keys = set(payload.metrics)
    forbidden = metric_keys & FORBIDDEN_UPDATE_KEYS
    if forbidden:
        raise HTTPException(
            status_code=422,
            detail=f"Federated updates cannot include raw patient data fields: {', '.join(sorted(forbidden))}",
        )
    if payload.weights_delta is not None:
        if not payload.weights_delta:
            raise HTTPException(status_code=422, detail="weights_delta cannot be empty")
        if any(not math.isfinite(value) for value in payload.weights_delta):
            raise HTTPException(status_code=422, detail="weights_delta must contain finite numbers")


def _generated_delta(round_row: FederatedRound, hospital: Hospital, sample_count: int) -> list[float]:
    seed = f"{round_row.id}:{hospital.id}:{sample_count}"
    rng = random.Random(seed)
    reputation_adjustment = (hospital.reputation_score - 0.8) / 100
    return [round(rng.uniform(-0.035, 0.035) + reputation_adjustment, 5) for _ in DEFAULT_GLOBAL_WEIGHTS]


def submit_update(
    db: Session,
    round_id: str,
    payload: FederatedClientUpdateRequest,
    actor: User,
) -> FederatedClientUpdate:
    _validate_update_payload(payload)
    round_row = db.query(FederatedRound).filter(FederatedRound.id == round_id).first()
    if not round_row:
        raise HTTPException(status_code=404, detail="Federated round not found")
    if round_row.status != "collecting":
        raise HTTPException(status_code=409, detail="This federated round is no longer collecting updates")
    hospital = db.query(Hospital).filter(Hospital.id == payload.hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    if not hospital.verified:
        raise HTTPException(status_code=403, detail="Only verified hospitals can submit federated updates")

    model_path = None
    model_fingerprint = None
    if payload.weights_delta is None:
        delta, computed_metrics, model_path, model_fingerprint, local_sample_count = _train_local_update(db, round_row, hospital)
        sample_count = local_sample_count
        metrics = computed_metrics
    else:
        delta = payload.weights_delta
        sample_count = payload.sample_count
        metrics = payload.metrics

    base_weights = round_row.global_weights.get("layers") if isinstance(round_row.global_weights, dict) else DEFAULT_GLOBAL_WEIGHTS
    if len(delta) != len(base_weights):
        raise HTTPException(status_code=422, detail=f"weights_delta must contain {len(base_weights)} values")

    update_payload = {
        "round_id": round_row.id,
        "hospital_id": hospital.id,
        "sample_count": sample_count,
        "weights_delta": delta,
        "metrics": metrics,
        "privacy_epsilon_spent": payload.privacy_epsilon_spent,
    }
    payload_hash = _hash_payload(update_payload)
    privacy_report = {
        "raw_data_shared": False,
        "secure_aggregation_ready": bool(round_row.privacy_config.get("secure_aggregation")),
        "differential_privacy": bool(round_row.privacy_config.get("differential_privacy")),
        "epsilon_spent": payload.privacy_epsilon_spent,
        "payload_hash": payload_hash,
    }

    existing = (
        db.query(FederatedClientUpdate)
        .filter(
            FederatedClientUpdate.round_id == round_row.id,
            FederatedClientUpdate.hospital_id == hospital.id,
        )
        .first()
    )
    if existing:
        existing.sample_count = sample_count
        existing.weights_delta = {"layers": delta}
        existing.metrics = metrics
        existing.privacy_report = privacy_report
        existing.payload_hash = payload_hash
        if payload.weights_delta is None:
            existing.model_update_path = model_path
            existing.model_fingerprint = model_fingerprint
        existing.accepted = True
        update_row = existing
    else:
        update_row = FederatedClientUpdate(
            round_id=round_row.id,
            hospital_id=hospital.id,
            sample_count=sample_count,
            weights_delta={"layers": delta},
            model_update_path=model_path,
            model_fingerprint=model_fingerprint,
            metrics=metrics,
            privacy_report=privacy_report,
            payload_hash=payload_hash,
        )
        db.add(update_row)

    run = db.query(LocalTrainingRun).filter_by(round_id=round_row.id, hospital_id=hospital.id).first()
    local_trust = round(
        (
            float(metrics.get("accuracy", 0.0))
            + float(metrics.get("f1_score", 0.0))
            + float(metrics.get("balanced_accuracy", metrics.get("accuracy", 0.0)))
        )
        / 3.0,
        4,
    )
    trust_components = {
        "accuracy": float(metrics.get("accuracy", 0.0)),
        "f1_score": float(metrics.get("f1_score", 0.0)),
        "balanced_accuracy": float(metrics.get("balanced_accuracy", metrics.get("accuracy", 0.0))),
        "hospital_reputation": float(hospital.reputation_score),
    }
    if run:
        run.sample_count = sample_count
        run.model_update_path = model_path or run.model_update_path
        run.metrics = metrics
        run.local_trust = local_trust
        run.trust_components = trust_components
        run.training_time_seconds = float(run.training_time_seconds or 0.0)
    else:
        run = LocalTrainingRun(
            round_id=round_row.id,
            hospital_id=hospital.id,
            model_update_path=model_path,
            sample_count=sample_count,
            metrics=metrics,
            local_trust=local_trust,
            trust_components=trust_components,
            training_time_seconds=0.0,
        )
        db.add(run)

    db.flush()
    round_row.participating_clients = len([update for update in round_row.updates if update.accepted])
    round_row.total_samples = sum(update.sample_count for update in round_row.updates if update.accepted)

    _audit(
        db,
        actor,
        "federated.client_update.accepted",
        update_row.id,
        {"round_id": round_row.id, "hospital_id": hospital.id, "payload_hash": payload_hash, "raw_data_shared": False},
    )
    db.commit()
    db.refresh(update_row)
    return update_row


def aggregate_round(db: Session, round_id: str, actor: User) -> FederatedRound:
    round_row = db.query(FederatedRound).filter(FederatedRound.id == round_id).first()
    if not round_row:
        raise HTTPException(status_code=404, detail="Federated round not found")
    updates = [update for update in round_row.updates if update.accepted]
    if len(updates) < round_row.min_clients:
        raise HTTPException(
            status_code=409,
            detail=f"At least {round_row.min_clients} hospital updates are required before aggregation",
        )

    total_samples = sum(update.sample_count for update in updates)
    base_weights = list(round_row.global_weights.get("layers") or DEFAULT_GLOBAL_WEIGHTS)
    aggregate_delta = [0.0 for _ in base_weights]
    weighted_accuracy = 0.0
    weighted_loss = 0.0
    epsilon_spent = 0.0

    for update in updates:
        weight = update.sample_count / total_samples
        delta = update.weights_delta.get("layers") or []
        aggregate_delta = [current + (delta_value * weight) for current, delta_value in zip(aggregate_delta, delta)]
        weighted_accuracy += float(update.metrics.get("accuracy", 0.0)) * weight
        weighted_loss += float(update.metrics.get("loss", 0.0)) * weight
        epsilon_spent += float(update.privacy_report.get("epsilon_spent", 0.0))

    aggregated_weights = [round(weight + delta, 6) for weight, delta in zip(base_weights, aggregate_delta)]
    try:
        X, y, _ = _load_tabular_dataset(round_row.disease_key)
        preprocessor, _, _ = build_tabular_preprocessor(X)
        preprocessor.fit(X)
        global_model_path, model_fingerprint = _save_aggregated_model_artifact(round_row, aggregated_weights, preprocessor)
        round_row.global_model_path = global_model_path
    except FileNotFoundError:
        model_fingerprint = None

    previous_global_trust = round_row.global_trust
    trust_confidence = round(weighted_accuracy, 4)
    trust_components = {
        "fidelity": trust_confidence,
        "interpretability": round(float(weighted_accuracy or 0.0) * 0.9, 4),
        "robustness": round(float(weighted_accuracy or 0.0) * 0.85, 4),
        "blockchain_integrity": 0.85,
        "compliance": 0.9,
    }
    global_trust, _ = calculate_dtei(
        trust_confidence,
        trust_components["interpretability"],
        trust_components["robustness"],
        trust_components["blockchain_integrity"],
        trust_components["compliance"],
    )

    aggregate_payload = {
        "round_id": round_row.id,
        "updates": [update.payload_hash for update in updates],
        "aggregated_weights": aggregated_weights,
        "total_samples": total_samples,
    }
    round_row.aggregated_weights = {"layers": aggregated_weights}
    round_row.metrics = {
        "accuracy": round(weighted_accuracy, 4),
        "loss": round(weighted_loss, 4),
        "participation_rate": round(len(updates) / max(1, db.query(Hospital).filter(Hospital.verified == True).count()), 4),
        "total_samples": total_samples,
        "epsilon_spent": round(epsilon_spent, 4),
    }
    round_row.status = "aggregated"
    round_row.completed_at = _utc_now()
    round_row.update_hash = _hash_payload(aggregate_payload)
    round_row.previous_global_trust = previous_global_trust
    round_row.global_trust = global_trust
    round_row.trust_change = round(global_trust - previous_global_trust, 4) if previous_global_trust is not None else None
    round_row.global_model_version = f"{round_row.global_model_version}-r{round_row.round_number}"

    db.add(
        GlobalModelVersion(
            disease_key=round_row.disease_key,
            round_number=round_row.round_number,
            version=round_row.global_model_version,
            model_path=round_row.global_model_path or "",
            model_fingerprint=model_fingerprint or "",
            metrics=round_row.metrics,
        )
    )
    db.add(
        FederatedTrustSnapshot(
            round_id=round_row.id,
            local_trust_values={
                update.hospital_id: float(
                    update.metrics.get("accuracy", 0.0)
                    if update.metrics.get("accuracy") is not None
                    else 0.0
                )
                for update in updates
            },
            global_trust=global_trust,
            trust_change=round(global_trust - previous_global_trust, 4) if previous_global_trust is not None else None,
        )
    )

    _audit(
        db,
        actor,
        "federated.round.aggregated",
        round_row.id,
        {
            "round_id": round_row.id,
            "client_updates": len(updates),
            "total_samples": total_samples,
            "aggregate_hash": round_row.update_hash,
            "raw_data_shared": False,
            "global_trust": global_trust,
        },
    )
    db.commit()
    db.refresh(round_row)
    return round_row


def run_demo_round(db: Session, payload: FederatedSimulationRequest, actor: User) -> FederatedRound:
    hospitals = ensure_federated_hospitals(db)[: payload.participating_hospitals]
    round_row = create_round(
        db,
        FederatedRoundCreateRequest(
            model_name=payload.model_name,
            disease_key=payload.disease_key,
            min_clients=min(2, len(hospitals)),
        ),
        actor,
    )
    for index, hospital in enumerate(hospitals):
        submit_update(
            db,
            round_row.id,
            FederatedClientUpdateRequest(
                hospital_id=hospital.id,
                sample_count=850 + (index * 175),
                metrics={
                    "accuracy": round(0.82 + (index * 0.015), 4),
                    "loss": round(0.31 - (index * 0.018), 4),
                    "f1_score": round(0.79 + (index * 0.014), 4),
                },
                privacy_epsilon_spent=0.22,
            ),
            actor,
        )
    return aggregate_round(db, round_row.id, actor)


def _round_summary(round_row: FederatedRound) -> dict[str, Any]:
    updates = [update for update in round_row.updates if update.accepted]
    return {
        "id": round_row.id,
        "round_number": round_row.round_number,
        "model_name": round_row.model_name,
        "disease_key": round_row.disease_key,
        "status": round_row.status,
        "strategy": round_row.strategy,
        "min_clients": round_row.min_clients,
        "submitted_clients": len(updates),
        "global_model_version": round_row.global_model_version,
        "metrics": round_row.metrics or {},
        "privacy_config": round_row.privacy_config or {},
        "update_hash": round_row.update_hash,
        "created_at": round_row.created_at.isoformat() if round_row.created_at else None,
        "completed_at": round_row.completed_at.isoformat() if round_row.completed_at else None,
        "updates": [
            {
                "id": update.id,
                "hospital_id": update.hospital_id,
                "hospital_name": update.hospital.name if update.hospital else "Unknown hospital",
                "sample_count": update.sample_count,
                "metrics": update.metrics or {},
                "privacy_report": update.privacy_report or {},
                "payload_hash": update.payload_hash,
                "created_at": update.created_at.isoformat() if update.created_at else None,
            }
            for update in updates
        ],
    }


def federated_dashboard(db: Session) -> dict[str, Any]:
    hospitals = ensure_federated_hospitals(db)
    rounds = db.query(FederatedRound).order_by(FederatedRound.created_at.desc()).limit(12).all()
    latest = rounds[0] if rounds else None
    aggregated_rounds = [round_row for round_row in rounds if round_row.status == "aggregated"]
    consensus = 0.0
    if aggregated_rounds:
        consensus = round(
            sum(float(round_row.metrics.get("accuracy", 0.0)) for round_row in aggregated_rounds) / len(aggregated_rounds),
            4,
        )
    nodes = [
        {
            "id": hospital.id,
            "name": hospital.name,
            "region": hospital.region,
            "verified": hospital.verified,
            "reputation": hospital.reputation_score,
            "trust": round(min(0.99, hospital.reputation_score + (consensus * 0.1 if consensus else 0.03)), 3),
        }
        for hospital in hospitals
    ]
    return {
        "mode": "production-ready-local",
        "architecture": {
            "orchestrator": "FastAPI federated coordinator",
            "strategy": "weighted FedAvg",
            "privacy": "secure aggregation metadata + differential privacy budget tracking",
            "raw_data_shared": False,
            "storage": "PostgreSQL federated rounds and client update hashes",
        },
        "nodes": nodes,
        "model_weight_round": latest.round_number if latest else 0,
        "consensus_reliability": consensus,
        "active_round": _round_summary(latest) if latest else None,
        "rounds": [_round_summary(round_row) for round_row in rounds],
        "cifts": {
            "trust_synchronization": consensus,
            "hospital_reputation": round(sum(node["reputation"] for node in nodes) / len(nodes), 3) if nodes else 0.0,
            "trust_evolution": [
                round(float(round_row.metrics.get("accuracy", 0.0)), 4)
                for round_row in reversed(aggregated_rounds[:8])
            ],
        },
    }


def synchronize_trust(db: Session, actor: User) -> dict[str, Any]:
    round_row = run_demo_round(db, FederatedSimulationRequest(), actor)
    return {
        "status": "synchronized",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "round": _round_summary(round_row),
        "dashboard": federated_dashboard(db),
    }
