from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import random
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, FederatedClientUpdate, FederatedRound, Hospital, User
from app.schemas import FederatedClientUpdateRequest, FederatedRoundCreateRequest, FederatedSimulationRequest

DEFAULT_GLOBAL_WEIGHTS = [0.42, -0.18, 0.31, 0.08, -0.27, 0.16, 0.23, -0.11]
DEFAULT_HOSPITALS = [
    ("TrustMedAI Reference Hospital", "Global", 0.88),
    ("City General Hospital", "North", 0.86),
    ("Lakeside Medical Center", "West", 0.84),
    ("Metro Health Institute", "Central", 0.89),
    ("Rural Care Network", "East", 0.81),
]
FORBIDDEN_UPDATE_KEYS = {"raw", "raw_data", "features", "patients", "patient_rows", "records", "dataset", "images"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_payload(payload: dict[str, Any]) -> str:
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
    round_row = FederatedRound(
        round_number=_next_round_number(db, payload.model_name),
        model_name=payload.model_name,
        disease_key=payload.disease_key,
        min_clients=payload.min_clients,
        global_model_version=payload.global_model_version,
        global_weights={"layers": DEFAULT_GLOBAL_WEIGHTS},
        privacy_config=_privacy_config(payload),
        metrics={"accuracy": 0.0, "loss": 0.0, "participation_rate": 0.0},
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

    delta = payload.weights_delta or _generated_delta(round_row, hospital, payload.sample_count)
    if len(delta) != len(DEFAULT_GLOBAL_WEIGHTS):
        raise HTTPException(status_code=422, detail=f"weights_delta must contain {len(DEFAULT_GLOBAL_WEIGHTS)} values")

    update_payload = {
        "round_id": round_row.id,
        "hospital_id": hospital.id,
        "sample_count": payload.sample_count,
        "weights_delta": delta,
        "metrics": payload.metrics,
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
        existing.sample_count = payload.sample_count
        existing.weights_delta = {"layers": delta}
        existing.metrics = payload.metrics
        existing.privacy_report = privacy_report
        existing.payload_hash = payload_hash
        existing.accepted = True
        update_row = existing
    else:
        update_row = FederatedClientUpdate(
            round_id=round_row.id,
            hospital_id=hospital.id,
            sample_count=payload.sample_count,
            weights_delta={"layers": delta},
            metrics=payload.metrics,
            privacy_report=privacy_report,
            payload_hash=payload_hash,
        )
        db.add(update_row)

    db.flush()
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
    round_row.global_model_version = f"{round_row.global_model_version}-r{round_row.round_number}"

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
