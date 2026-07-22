from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
import json
from typing import Any

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import BACKEND_ROOT, settings
from app.db.models import DiagnosisArtifact, DiagnosisRecord, User
from app.services.catalog import get_disease
from app.services.storage import read_object, store_object

IST = timezone(timedelta(hours=5, minutes=30))

DISCLAIMER = (
    "This AI-generated report is intended for preliminary screening and decision support only. "
    "It is not a substitute for professional medical diagnosis, clinical examination, or treatment. "
    "Patients should consult a qualified healthcare professional for confirmation and medical advice."
)


def _safe(value: Any, fallback: str = "Not Available") -> str:
    if value is None:
        return fallback
    if isinstance(value, float):
        return f"{value:.3f}"
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "undefined"}:
        return fallback
    return text


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_ist(value: datetime | None) -> str:
    if not value:
        return "Not Available"
    return _as_utc(value).astimezone(IST).strftime("%Y-%m-%d %I:%M:%S %p IST")


def _date(value: datetime | None) -> str:
    return _format_ist(value)


def _calculate_age(date_of_birth: str | None) -> int | None:
    if not date_of_birth:
        return None
    try:
        born = datetime.fromisoformat(date_of_birth[:10]).date()
    except ValueError:
        return None
    today = _utc_now().date()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _patient_profile(record: DiagnosisRecord, patient: User | None) -> dict[str, Any]:
    profile = dict(patient.profile or {}) if patient and isinstance(patient.profile, dict) else {}
    full_name = patient.full_name if patient else record.patient_name
    email = patient.email if patient else record.patient_email
    age = _calculate_age(profile.get("date_of_birth"))
    return {
        "Full Name": _safe(full_name),
        "Patient ID": _safe(patient.public_patient_id if patient else None),
        "Age": _safe(age),
        "Date of Birth": _safe(profile.get("date_of_birth")),
        "Sex": _safe(profile.get("sex")),
        "Gender": _safe(profile.get("gender")),
        "Blood Group": _safe(profile.get("blood_group")),
        "Phone": _safe(profile.get("phone_number")),
        "Email": _safe(email),
        "Address": _safe(
            ", ".join(
                part
                for part in [
                    profile.get("address"),
                    profile.get("city"),
                    profile.get("state"),
                    profile.get("country"),
                ]
                if part
            )
        ),
        "Emergency Contact": _safe(
            " / ".join(
                part
                for part in [profile.get("emergency_contact_name"), profile.get("emergency_contact_phone")]
                if part
            )
        ),
        "Medical Information": _safe(profile.get("medical_information")),
        "Registration Date": _date(patient.created_at if patient else None),
        "Last Profile Update": _date(patient.profile_updated_at if patient else None),
    }


def _diagnosis_status(prediction: str) -> str:
    normalized = prediction.lower()
    if any(token in normalized for token in ("normal", "negative", "healthy", "low_risk", "controlled", "no_tumor")):
        return "Not Detected / Low Risk"
    if "risk" in normalized:
        return "Elevated Risk"
    return "Detected / Positive"


def _recommendation(record: DiagnosisRecord) -> str:
    status = _diagnosis_status(record.prediction)
    disease_name = get_disease(record.disease_key).name
    if "Not Detected" in status:
        return (
            f"The AI result does not currently indicate {disease_name.lower()}. Continue routine monitoring, "
            "maintain preventive care, and consult a qualified clinician if symptoms persist or worsen."
        )
    return (
        f"The AI result suggests {disease_name.lower()} may require clinical attention. Schedule a medical review, "
        "share this report with a qualified healthcare professional, and follow emergency care guidance if severe symptoms occur."
    )


def _model_name(record: DiagnosisRecord) -> str:
    metadata_path = BACKEND_ROOT / "app" / "ai" / "artifacts" / f"{record.disease_key}_model_metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        selected = metadata.get("selected_model")
        version = metadata.get("artifact_version")
        if selected and version:
            return f"{selected} / artifact v{version}"
        return _safe(selected)
    except Exception:
        return "Not Available"


def _table(rows: list[tuple[str, Any]], col_widths: list[float] | None = None) -> Table:
    body = [[Paragraph(f"<b>{_safe(label)}</b>", STYLES["Body"]), Paragraph(_safe(value), STYLES["Body"])] for label, value in rows]
    table = Table(body, colWidths=col_widths or [1.9 * inch, 4.6 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef7f5")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _section(title: str) -> list[Any]:
    return [Spacer(1, 0.12 * inch), Paragraph(title, STYLES["Section"]), Spacer(1, 0.06 * inch)]


def _image_from_bytes(content: bytes, width: float, height: float) -> Image | None:
    try:
        image = Image(BytesIO(content))
        ratio = min(width / image.imageWidth, height / image.imageHeight)
        image.drawWidth = image.imageWidth * ratio
        image.drawHeight = image.imageHeight * ratio
        return image
    except Exception:
        return None


def _profile_photo(patient: User | None) -> Any:
    if patient and patient.profile_photo_object_path:
        try:
            image = _image_from_bytes(read_object(patient.profile_photo_object_path), 1.1 * inch, 1.1 * inch)
            if image:
                return image
        except Exception:
            pass
    initial = (patient.full_name[:1] if patient and patient.full_name else "P").upper()
    avatar = Table(
        [[Paragraph(initial, ParagraphStyle("AvatarText", parent=STYLES["Title"], alignment=TA_CENTER, textColor=colors.white))]],
        colWidths=[1.1 * inch],
        rowHeights=[1.1 * inch],
    )
    avatar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f766e")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return avatar


def _qr_flowable(value: str) -> Drawing:
    qr = QrCodeWidget(value)
    bounds = qr.getBounds()
    size = 1.15 * inch
    drawing = Drawing(size, size, transform=[size / (bounds[2] - bounds[0]), 0, 0, size / (bounds[3] - bounds[1]), 0, 0])
    drawing.add(qr)
    return drawing


def _input_image(record: DiagnosisRecord) -> Image | None:
    artifact = next((item for item in record.artifacts if item.kind == "input_image"), None)
    if not isinstance(artifact, DiagnosisArtifact):
        return None
    try:
        return _image_from_bytes(read_object(artifact.object_path), 4.7 * inch, 2.8 * inch)
    except Exception:
        return None


def _explainability_rows(record: DiagnosisRecord) -> list[tuple[str, Any]]:
    explanation = record.explanation or {}
    rows: list[tuple[str, Any]] = []
    for key, label in [
        ("shap", "SHAP Analysis"),
        ("lime", "LIME Analysis"),
        ("gradcam", "Grad-CAM"),
        ("integrated_gradients", "Integrated Gradients"),
    ]:
        value = explanation.get(key)
        if isinstance(value, dict):
            if value.get("available") is True:
                rows.append((label, json.dumps(value, default=str)[:900]))
            else:
                rows.append((label, value.get("reason") or "Not Available"))
    feature_importance = None
    shap = explanation.get("shap")
    if isinstance(shap, dict):
        feature_importance = shap.get("feature_importance")
    if isinstance(feature_importance, list) and feature_importance:
        top = feature_importance[:8]
        rows.append(("Important Factors", "; ".join(json.dumps(item, default=str) for item in top)))
    if not rows:
        rows.append(("AI Explainability", "No model-bound explanation artifact is available for this diagnosis."))
    return rows


def _percent(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Not Evaluated"
    if not number == number:
        return "Not Evaluated"
    percent = number * 100 if number <= 1 else number
    return f"{percent:.1f}%"


def _adversarial_rows(record: DiagnosisRecord) -> list[tuple[str, Any]]:
    adversarial = (record.metrics or {}).get("adversarial", {})
    if not isinstance(adversarial, dict):
        adversarial = {}
    patient_attack = adversarial.get("patient_attack") if isinstance(adversarial.get("patient_attack"), dict) else {}
    before = adversarial.get("before_attack_metrics") if isinstance(adversarial.get("before_attack_metrics"), dict) else {}
    under = adversarial.get("under_attack_metrics") if isinstance(adversarial.get("under_attack_metrics"), dict) else {}
    impact = adversarial.get("attack_impact") if isinstance(adversarial.get("attack_impact"), dict) else {}
    defense = adversarial.get("defense") if isinstance(adversarial.get("defense"), dict) else {}
    aecs_details = adversarial.get("aecs") if isinstance(adversarial.get("aecs"), dict) else {}
    return [
        ("Model", adversarial.get("model_name")),
        ("Model Version", adversarial.get("model_version")),
        ("Input Modality", adversarial.get("input_modality") or record.input_modality),
        ("Evaluation Dataset", adversarial.get("evaluation_dataset")),
        ("Random Seed", adversarial.get("random_seed")),
        ("Attack Type", patient_attack.get("attack_type") or adversarial.get("attack_type")),
        ("Patient-Specific Confidence", _percent(record.confidence)),
        ("Original Model Clean/Test Accuracy", _percent(before.get("accuracy"))),
        ("Aggregate Under-Attack Accuracy", _percent(adversarial.get("after_attack_accuracy") or under.get("accuracy"))),
        ("Accuracy Degradation", _percent(impact.get("accuracy_degradation"))),
        ("Prediction Before Attack", patient_attack.get("prediction_before_attack")),
        ("Prediction Under Attack", patient_attack.get("prediction_under_attack")),
        ("Prediction Changed", patient_attack.get("prediction_changed")),
        ("Robustness Score", _percent(adversarial.get("robustness_score"))),
        ("AECS", adversarial.get("aecs_reason") if adversarial.get("aecs_available") is False else _percent(record.aecs)),
        ("Defense Evaluation", defense.get("training_status") or defense.get("status") or "Not Yet Evaluated"),
        ("Evidence-Based Conclusion", adversarial.get("conclusion")),
    ]


def _adversarial_artifact_rows(record: DiagnosisRecord) -> list[tuple[str, Any]]:
    labels = {
        "input_image": "Original Medical Image",
        "adversarial_image": "Adversarially Perturbed Image",
        "perturbation_map": "Adversarial Perturbation Map",
        "affected_region_overlay": "Affected Region Overlay",
    }
    rows: list[tuple[str, Any]] = []
    for kind, label in labels.items():
        artifact = next((item for item in record.artifacts if item.kind == kind), None)
        rows.append((label, artifact.original_filename if isinstance(artifact, DiagnosisArtifact) else "Not Available"))
    return rows


def _adversarial_artifact_image_table(label: str, image: Image) -> Table:
    table = Table(
        [[Paragraph(f"<b>{label}</b>", STYLES["Body"])], [image]],
        colWidths=[3.3 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _adversarial_artifact_images(record: DiagnosisRecord) -> list[Table]:
    labels = {
        "adversarial_image": "Adversarially Perturbed Image",
        "perturbation_map": "Adversarial Perturbation Map",
        "affected_region_overlay": "Affected Region Overlay",
    }
    images: list[Table] = []
    for kind, label in labels.items():
        artifact = next((item for item in record.artifacts if item.kind == kind), None)
        if isinstance(artifact, DiagnosisArtifact):
            try:
                image = _image_from_bytes(read_object(artifact.object_path), 3.3 * inch, 2.4 * inch)
                if image is not None:
                    images.append(_adversarial_artifact_image_table(label, image))
            except Exception:
                continue
    return images


def _report_payload_hash(record: DiagnosisRecord, patient_profile: dict[str, Any], verification_id: str) -> str:
    payload = {
        "diagnosis_id": record.id,
        "patient_id": patient_profile.get("Patient ID"),
        "disease_key": record.disease_key,
        "prediction": record.prediction,
        "confidence": record.confidence,
        "trust_score": record.trust_score,
        "blockchain_hash": record.blockchain_hash,
        "verification_id": verification_id,
        "generated_at": _utc_now().isoformat(),
    }
    return sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _footer(canvas, doc) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(doc.leftMargin, 0.38 * inch, "TrustMedAI-Chain | Confidential AI decision-support report")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


STYLES = getSampleStyleSheet()
STYLES.add(ParagraphStyle("ReportTitle", parent=STYLES["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#0f172a")))
STYLES.add(ParagraphStyle("Section", parent=STYLES["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#0f766e"), spaceBefore=8))
STYLES.add(ParagraphStyle("Body", parent=STYLES["BodyText"], fontName="Helvetica", fontSize=9, leading=12))
STYLES.add(ParagraphStyle("Small", parent=STYLES["BodyText"], fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#475569")))
STYLES.add(ParagraphStyle("Disclaimer", parent=STYLES["BodyText"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.HexColor("#7f1d1d")))


def build_pdf_report(record: DiagnosisRecord, patient: User | None = None) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.52 * inch,
        bottomMargin=0.62 * inch,
        title=f"TrustMedAI Diagnosis {record.id}",
    )
    disease = get_disease(record.disease_key)
    generated_at = _utc_now()
    verification_id = f"trustmedai:{record.id}:{record.blockchain_hash[:16]}"
    verification_url = f"{settings.frontend_origin.rstrip('/')}/verify-report/{record.id}?v={record.blockchain_hash[:16]}"
    profile = _patient_profile(record, patient)
    report_hash = _report_payload_hash(record, profile, verification_id)

    story: list[Any] = []
    header = Table(
        [
            [
                [
                    Paragraph("TrustMedAI-Chain", STYLES["Section"]),
                    Paragraph("AI-Powered Multi-Disease Diagnosis Report", STYLES["ReportTitle"]),
                    Paragraph(f"Report ID: {record.id}", STYLES["Small"]),
                    Paragraph(f"Generated: {_format_ist(generated_at)}", STYLES["Small"]),
                ],
                _qr_flowable(verification_id),
            ]
        ],
        colWidths=[5.35 * inch, 1.35 * inch],
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#99f6e4")), ("PADDING", (0, 0), (-1, -1), 10)]))
    story.extend([header, Spacer(1, 0.12 * inch)])

    story.extend(_section("1. Patient Information"))
    patient_rows = [(key, value) for key, value in profile.items() if key not in {"Medical Information"}]
    story.append(Table([[ _profile_photo(patient), _table(patient_rows, [1.55 * inch, 4.15 * inch]) ]], colWidths=[1.25 * inch, 5.65 * inch]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(_table([("Medical Information", profile["Medical Information"])]))

    story.extend(_section("2. Diagnosis Information"))
    story.append(
        _table(
            [
                ("Disease Name", disease.name),
                ("Diagnosis Result", record.prediction.replace("_", " ").title()),
                ("Result Status", _diagnosis_status(record.prediction)),
                ("Prediction Confidence", f"{record.confidence * 100:.1f}%"),
                ("AI Trust Score", f"{record.trust_score * 100:.1f}%"),
                ("Diagnosis Date", _date(record.created_at)),
                ("Model Name / Version", _model_name(record)),
                ("Input Modality", record.input_modality.title()),
            ]
        )
    )

    story.extend(_section("3. Doctor Clinical Review"))
    story.append(
        _table(
            [
                ("Original AI Result", record.prediction.replace("_", " ").title()),
                ("Review Status", record.review_status),
                ("Doctor Decision", record.doctor_decision),
                ("Final Clinical Decision", record.final_clinical_decision),
                ("Review Notes", record.review_notes),
                ("Reviewed By Doctor ID", record.reviewed_by_id),
                ("Review Timestamp", _date(record.reviewed_at)),
            ]
        )
    )

    story.extend(_section("4. Medical Input Data"))
    visible_inputs = []
    for key, value in sorted((record.input_features or {}).items()):
        if key in {"image_filename"}:
            continue
        visible_inputs.append((key.replace("_", " ").title(), json.dumps(value, default=str) if isinstance(value, (dict, list)) else value))
    story.append(_table(visible_inputs or [("Input Data", "No structured clinical input values were recorded.")]))
    image = _input_image(record)
    if image:
        story.extend([Spacer(1, 0.08 * inch), Paragraph("Uploaded Medical Image", STYLES["Section"]), image])

    story.extend(_section("5. Adversarial Robustness Analysis"))
    story.append(_table(_adversarial_rows(record)))
    if record.input_modality == "image":
        story.append(Spacer(1, 0.08 * inch))
        story.append(_table(_adversarial_artifact_rows(record)))
        adversarial_images = _adversarial_artifact_images(record)
        if adversarial_images:
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph("Adversarial Image Artifacts", STYLES["Section"]))
            story.append(Spacer(1, 0.04 * inch))
            rows: list[list[Any]] = []
            for i in range(0, len(adversarial_images), 2):
                row = [adversarial_images[i]]
                if i + 1 < len(adversarial_images):
                    row.append(adversarial_images[i + 1])
                else:
                    row.append("")
                rows.append(row)
            artifact_table = Table(rows, colWidths=[3.45 * inch, 3.45 * inch], hAlign="LEFT")
            artifact_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(artifact_table)
        story.append(Spacer(1, 0.04 * inch))
        story.append(
            Paragraph(
                "Attack perturbation artifacts show measured input changes and are distinct from model explanation heatmaps.",
                STYLES["Small"],
            )
        )

    story.extend(_section("6. AI Explainability"))
    story.append(_table(_explainability_rows(record)))

    story.extend(_section("7. Recommendations"))
    story.append(Paragraph(_recommendation(record), STYLES["Body"]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(DISCLAIMER, STYLES["Disclaimer"]))

    story.extend(_section("8. Blockchain Verification"))
    blockchain = record.blockchain_status or {}
    ethereum = blockchain.get("ethereum", {}) if isinstance(blockchain.get("ethereum"), dict) else {}
    fabric = blockchain.get("fabric", {}) if isinstance(blockchain.get("fabric"), dict) else {}
    local_ledger = blockchain.get("local_ledger", {}) if isinstance(blockchain.get("local_ledger"), dict) else {}
    story.append(
        _table(
            [
                ("Verification Status", "Verified" if record.ethereum_anchor_verified or record.fabric_anchor_verified or local_ledger.get("verified") else "Local hash verified / external chain unavailable"),
                ("Blockchain Hash", record.blockchain_hash),
                ("Ethereum Transaction Hash", record.ethereum_tx_hash or ethereum.get("tx_hash")),
                ("Ethereum Block Number", record.ethereum_block_number or ethereum.get("block_number")),
                ("Fabric Transaction ID", record.fabric_tx_id or fabric.get("tx_id")),
                ("Local Ledger Block Number", local_ledger.get("block_number")),
                ("Local Ledger Transaction ID", local_ledger.get("tx_id")),
                ("Local Ledger Block Hash", local_ledger.get("block_hash")),
                ("Local Ledger Timestamp", _date(datetime.fromisoformat(str(local_ledger["timestamp"])) if local_ledger.get("timestamp") else None)),
                ("Network", blockchain.get("network") or local_ledger.get("network")),
                ("Consensus", blockchain.get("consensus") or local_ledger.get("consensus")),
                ("Network Information", json.dumps(blockchain, default=str)[:1200]),
                ("Verification Identifier", verification_id),
                ("Verification URL", verification_url),
            ]
        )
    )

    story.extend(_section("9. Digital Signature / Integrity"))
    story.append(
        _table(
            [
                ("Report Payload Hash", report_hash),
                ("Blockchain Hash", record.blockchain_hash),
                ("Verification Status", "Ready for authenticity verification without exposing patient data."),
                ("Generated Timestamp", _format_ist(generated_at)),
            ]
        )
    )

    story.extend(_section("9. Stored Artifacts"))
    artifact_rows = [
        (
            artifact.kind.replace("_", " ").title(),
            f"{artifact.original_filename} | {artifact.content_type} | {artifact.size_bytes} bytes | SHA-256 {artifact.sha256}",
        )
        for artifact in record.artifacts
    ]
    story.append(_table(artifact_rows or [("Artifacts", "No uploaded artifacts were stored for this diagnosis.")]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def refresh_stored_pdf_report(record: DiagnosisRecord, patient: User | None = None) -> DiagnosisArtifact:
    content = build_pdf_report(record, patient)
    artifact = next((item for item in record.artifacts if item.kind == "generated_report"), None)
    if artifact is None:
        stored = store_object(
            f"diagnoses/{record.id}/generated_report-{record.id}.pdf",
            content,
            "application/pdf",
        )
        artifact = DiagnosisArtifact(
            diagnosis_id=record.id,
            kind="generated_report",
            object_path=stored.object_path,
            original_filename=f"trustmedai-{record.id}.pdf",
            content_type="application/pdf",
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
        )
        record.artifacts.append(artifact)
        return artifact

    object_name = artifact.object_path
    if object_name.startswith("local:"):
        object_name = object_name.removeprefix("local:")
    elif object_name.startswith("minio:"):
        object_name = object_name.removeprefix("minio:")
    stored = store_object(object_name, content, "application/pdf")
    artifact.object_path = stored.object_path
    artifact.size_bytes = len(content)
    artifact.sha256 = sha256(content).hexdigest()
    artifact.content_type = "application/pdf"
    return artifact
