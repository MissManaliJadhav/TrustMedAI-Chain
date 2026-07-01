from io import BytesIO

import cv2
import numpy as np
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.db.models import DiagnosisRecord, User
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


def test_tabular_and_image_artifacts_persist_end_to_end(tmp_path) -> None:
    settings.artifact_storage_backend = "local"
    settings.local_artifact_dir = str(tmp_path)

    with TestClient(app) as client:
        headers = _admin_headers(client)
        schema = client.get("/api/v1/datasets/diseases/diabetes/features").json()["features"]
        features = {item["name"]: item["default"] for item in schema}
        pdf = _pdf_bytes()
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
        assert {item["kind"] for item in image_body["artifacts"]} == {
            "input_image",
            "supporting_pdf",
            "generated_report",
        }

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

    db = SessionLocal()
    try:
        record = db.query(DiagnosisRecord).filter(DiagnosisRecord.id == image_body["diagnosis_id"]).one()
        assert record.input_features["image_width"] == 64
        assert len(record.artifacts) == 3
        assert all(len(artifact.sha256) == 64 for artifact in record.artifacts)
        assert all(read_object(artifact.object_path) for artifact in record.artifacts)
        actor = db.query(User).filter(User.id == record.doctor_id).one()
        assert hash_payload(build_diagnosis_anchor_payload(record, actor)) == record.blockchain_hash
    finally:
        db.close()
