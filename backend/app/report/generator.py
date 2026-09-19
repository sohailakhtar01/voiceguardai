"""Forensic report — a case-style JSON record and a printable PDF for an
analysis result. Used by /api/analyze/full (metadata) and /api/report/pdf."""

import hashlib
import io
import uuid
from datetime import datetime, timezone

TIER_HEX = {"low": "#16a34a", "medium": "#d97706", "high": "#ea580c", "critical": "#dc2626"}

DISCLAIMER = (
    "Automated analysis by VoiceGuard AI. No voice-clone detector is 100% accurate "
    "on unseen tools; treat this as investigative support, not sole proof."
)


def new_case_id() -> str:
    return "VG-" + uuid.uuid4().hex[:10].upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_report(case_id, created_at, audio_sha256, voice, identity, intent, risk) -> dict:
    """Assemble a structured forensic record. All inputs are plain dicts."""
    return {
        "case_id": case_id,
        "created_at": created_at,
        "tool": "VoiceGuard AI",
        "audio_sha256": audio_sha256,
        "verdict": {
            "tier": risk["tier"],
            "risk": risk["overall_risk"],
            "response": risk["response"],
        },
        "reasons": risk["reasons"],
        "voice": voice,
        "identity": identity,
        "intent": intent,
        "disclaimer": DISCLAIMER,
    }


def render_pdf(report: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=17, spaceAfter=2)
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=10, leading=14)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8, textColor=colors.grey)
    mono = ParagraphStyle("mono", parent=ss["Normal"], fontSize=8, fontName="Courier")

    tier = report["verdict"]["tier"]
    color = colors.HexColor(TIER_HEX.get(tier, "#334155"))
    flow = []

    flow.append(Paragraph("VoiceGuard AI — Voice Impersonation Forensic Report", h1))
    flow.append(Paragraph(f"Case {report['case_id']} &middot; {report['created_at']}", small))
    flow.append(Spacer(1, 10))

    verdict = Table(
        [[Paragraph(
            f"<b>{tier.upper()}</b> &nbsp; risk {int(report['verdict']['risk'] * 100)}%"
            f"<br/>{report['verdict']['response']}",
            ParagraphStyle("v", parent=body, textColor=colors.white, fontSize=12),
        )]],
        colWidths=[doc.width],
    )
    verdict.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    flow.append(verdict)
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("<b>Findings</b>", body))
    for r in report["reasons"]:
        flow.append(Paragraph("&bull; " + r, body))
    flow.append(Spacer(1, 10))

    v = report.get("voice") or {}
    idr = report.get("identity") or {}
    intent = report.get("intent") or {}
    rows = [["Signal", "Result"]]
    if report.get("voice"):
        rows.append([
            "Voice authenticity",
            f"{v.get('label', '?')} ({int(v.get('synthetic_probability', 0) * 100)}% synthetic)",
        ])
    if report.get("identity"):
        state = ("match" if idr.get("identity_match")
                 else "no match" if idr.get("checked") else "not checked")
        rows.append(["Identity", state])
    if report.get("intent"):
        rows.append(["Scam intent", ", ".join(intent.get("triggered", [])) or "none"])
    rows.append(["Audio SHA-256",
                 Paragraph(report.get("audio_sha256") or "n/a (text only)", mono)])
    table = Table(rows, colWidths=[doc.width * 0.32, doc.width * 0.68])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    flow.append(table)
    flow.append(Spacer(1, 10))

    if intent.get("transcript"):
        flow.append(Paragraph("<b>Transcript</b>", body))
        flow.append(Paragraph(intent["transcript"], body))
        flow.append(Spacer(1, 10))

    flow.append(Paragraph(report["disclaimer"], small))
    doc.build(flow)
    return buf.getvalue()
