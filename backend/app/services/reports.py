from io import BytesIO
import json
from textwrap import wrap

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.db.models import DiagnosisRecord



def build_pdf_report(record: DiagnosisRecord) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    pdf.setTitle(f"TrustMedAI Diagnosis {record.id}")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(48, height - 64, "TrustMedAI-Chain Diagnosis Report")
    pdf.setFont("Helvetica", 11)
    y = height - 100

    def draw_line(text: str, *, bold: bool = False) -> None:
        nonlocal y
        for line in wrap(text, width=96) or [""]:
            if y < 54:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - 54
            pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
            pdf.drawString(48, y, line)
            y -= 15

    lines = [
        f"Diagnosis ID: {record.id}",
        f"Patient: {record.patient_name or 'Not provided'}",
        f"Patient Email: {record.patient_email or 'Not provided'}",
        f"Disease: {record.disease_key}",
        f"Prediction: {record.prediction}",
        f"Confidence: {record.confidence:.3f}",
        f"Trust Score: {record.trust_score:.3f}",
        f"AECS: {record.aecs:.3f}",
        f"Input Modality: {record.input_modality}",
        f"Blockchain Hash: {record.blockchain_hash}",
        f"Ethereum Transaction: {record.ethereum_tx_hash or 'Not anchored'}",
        f"Fabric Transaction: {record.fabric_tx_id or 'Not anchored'}",
        f"Doctor Notes: {record.doctor_notes or 'None'}",
    ]
    for line in lines:
        draw_line(line)

    y -= 8
    draw_line("Clinical Model Inputs", bold=True)
    for name, value in sorted((record.input_features or {}).items()):
        draw_line(f"{name}: {value}")

    y -= 8
    draw_line("Stored Artifacts", bold=True)
    if record.artifacts:
        for artifact in record.artifacts:
            draw_line(
                f"{artifact.kind}: {artifact.original_filename} "
                f"({artifact.content_type}, {artifact.size_bytes} bytes, SHA-256 {artifact.sha256})"
            )
    else:
        draw_line("No uploaded artifacts.")

    y -= 8
    draw_line("Model Metrics", bold=True)
    draw_line(json.dumps(record.metrics or {}, sort_keys=True))
    y -= 8
    draw_line("Blockchain Status", bold=True)
    draw_line(json.dumps(record.blockchain_status or {}, sort_keys=True, default=str))
    y -= 8
    draw_line("Research-use decision support only; this report is not a substitute for clinical diagnosis.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
