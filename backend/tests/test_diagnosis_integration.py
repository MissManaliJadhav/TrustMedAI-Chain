from io import BytesIO
from uuid import uuid4

import cv2
import numpy as np
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.db.models import AuditEvent, DiagnosisRecord, Notification, User
from app.db.session import SessionLocal
from app.main import app
from app.services.blockchain import build_diagnosis_anchor_payload, hash_payload
from app.services.storage import read_object


def _pdf_bytes() -> bytes:
    buffer = BytesIO()
    document = canvas.Canvas(buffer)
    document.drawString(50, 800, "Supporting clinical report")
    document.save()
    return buffer.getvalue()


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.super_admin_email, "password": settings.super_admin_password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _doctor_headers(client: TestClient) -> dict[str, str]:
    email = f"doctor-{uuid4().hex[:8]}@example.com"
    password = "StrongPass123!"
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "full_name": "Integration Doctor", "role": "DOCTOR"},
    )
    assert signup.status_code == 201
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_tabular_and_image_artifacts_persist_end_to_end(tmp_path) -> None:
    settings.artifact_storage_backend = "local"
    settings.local_artifact_dir = str(tmp_path)

    with TestClient(app) as client:
        admin_headers = _admin_headers(client)
        headers = _doctor_headers(client)
        schema = client.get("/api/v1/datasets/diseases/diabetes/features").json()["features"]
        features = {item["name"]: item["default"] for item in schema}
        pdf = _pdf_bytes()
        forbidden_admin_prediction = client.post(
            "/api/v1/predictions/tabular",
            headers=admin_headers,
            data={
                "disease_key": "diabetes",
                "patient_name": "Admin Forbidden Patient",
                "patient_email": "admin-forbidden@example.com",
                "features_json": __import__("json").dumps(features),
            },
        )
        assert forbidden_admin_prediction.status_code == 403

        tabular = client.post(
            "/api/v1/predictions/tabular",
            headers=headers,
            data={
                "disease_key": "diabetes",
                "patient_name": "Persistence Patient",
                "patient_email": "persistence@example.com",
                "features_json": __import__("json").dumps(features),
            },
            files={"supporting_pdf": ("labs.pdf", pdf, "application/pdf")},
        )
        assert tabular.status_code == 200, tabular.text
        tabular_body = tabular.json()
        assert tabular_body["input_modality"] == "tabular"
        assert {item["kind"] for item in tabular_body["artifacts"]} == {
            "supporting_pdf",
            "generated_report",
        }
        tabular_ledger = tabular_body["blockchain_status"]["local_ledger"]
        assert tabular_ledger["verified"] is True
        assert tabular_ledger["block_number"] >= 1
        assert tabular_ledger["tx_id"].startswith("TX-")
        assert tabular_ledger["network"] == "TrustMedAI-Chain Local Ledger"
        assert tabular_body["blockchain_status"]["ledger_status"] == "immutable"
        assert tabular_body["dtei_components"]["blockchain_integrity"] == 1.0
        dtei = tabular_body["metrics"]["dtei"]
        assert dtei["formula"] == "DTEI = alpha*F + beta*I + gamma*R + delta*B + lambda*C"
        assert round(sum(dtei["weights"].values()), 5) == 1.0
        assert dtei["status"] in {"High Trust", "Moderate Trust", "Low Trust", "Critical Review Required"}
        assert tabular_body["adversarial"]["patient_attack"]["status"] in {"Evaluated", "Not Evaluated"}
        assert "before_attack_metrics" in tabular_body["adversarial"]
        assert "under_attack_metrics" in tabular_body["adversarial"]

        image = np.zeros((64, 64, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".png", image)
        assert ok
        image_response = client.post(
            "/api/v1/predictions/image",
            headers=headers,
            data={
                "disease_key": "pneumonia",
                "patient_name": "Image Persistence Patient",
                "patient_email": "image-persistence@example.com",
            },
            files={
                "image": ("scan.png", encoded.tobytes(), "image/png"),
                "supporting_pdf": ("radiology.pdf", pdf, "application/pdf"),
            },
        )
        assert image_response.status_code == 200, image_response.text
        image_body = image_response.json()
        assert image_body["input_modality"] == "image"
        assert image_body["adversarial"]["security_event"]["generated"] is True
        assert image_body["adversarial"]["trust_evolution"]["trust_change"] <= 0
        assert {item["kind"] for item in image_body["artifacts"]} == {
            "input_image",
            "gradcam_heatmap",
            "adversarial_image",
            "perturbation_map",
            "affected_region_overlay",
            "supporting_pdf",
            "generated_report",
        }
        assert image_body["adversarial"]["patient_attack"]["status"] == "Evaluated"
        assert set(image_body["adversarial"]["patient_attack"]["visual_artifact_kinds"]) == {
            "input_image",
            "adversarial_image",
            "perturbation_map",
            "affected_region_overlay",
        }
        assert image_body["adversarial"]["patient_attack"]["percentage_pixels_affected"] >= 0

        report = client.get(
            f"/api/v1/reports/{image_body['diagnosis_id']}.pdf",
            headers=headers,
        )
        assert report.status_code == 200
        assert report.content.startswith(b"%PDF-")

        verification = client.get(
            f"/api/v1/blockchain/verify/{image_body['diagnosis_id']}",
            headers=headers,
        )
        assert verification.status_code == 200
        assert verification.json()["local_hash_match"] is True
        assert verification.json()["local_ledger"]["verified"] is True
        assert verification.json()["verified"] is True

    db = SessionLocal()
    try:
        record = db.query(DiagnosisRecord).filter(DiagnosisRecord.id == image_body["diagnosis_id"]).one()
        assert record.input_features["image_width"] == 64
        assert len(record.artifacts) == 7
        assert all(len(artifact.sha256) == 64 for artifact in record.artifacts)
        assert all(read_object(artifact.object_path) for artifact in record.artifacts)
        security_notifications = db.query(Notification).filter(
            Notification.diagnosis_id == record.id,
            Notification.notification_type == "adversarial_security_event",
        ).all()
        assert security_notifications
        assert any(notification.severity in {"warning", "critical"} for notification in security_notifications)
        security_audit = db.query(AuditEvent).filter(
            AuditEvent.resource_id == record.id,
            AuditEvent.action == "security.adversarial_event_detected",
        ).first()
        assert security_audit is not None
        actor = db.query(User).filter(User.id == record.doctor_id).one()
        assert hash_payload(build_diagnosis_anchor_payload(record, actor)) == record.blockchain_hash
    finally:
        db.close()
