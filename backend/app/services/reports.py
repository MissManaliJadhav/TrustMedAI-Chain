from io import BytesIO

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
    lines = [
        f"Diagnosis ID: {record.id}",
        f"Disease: {record.disease_key}",
        f"Prediction: {record.prediction}",
        f"Confidence: {record.confidence:.3f}",
        f"Trust Score: {record.trust_score:.3f}",
        f"AECS: {record.aecs:.3f}",
        f"Blockchain Hash: {record.blockchain_hash}",
        f"Doctor Notes: {record.doctor_notes or 'None'}",
    ]
    for line in lines:
        pdf.drawString(48, y, line[:115])
        y -= 20
    pdf.drawString(48, y - 12, "Explanation and metrics are available through the API audit record.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
