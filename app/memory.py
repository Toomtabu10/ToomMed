"""
Turns a patient's stored data into (a) context for the model and
(b) chat history for continuity — the two forms of "memory" this
project supports.
"""

from typing import List, Dict
from sqlalchemy.orm import Session

from . import models

MAX_HISTORY_MESSAGES = 20  # most recent N messages included in every chat call


def build_patient_context(patient: models.Patient) -> str:
    """
    Renders the patient's structured facts into a compact text block the
    model reads as background — not something it can edit. If nothing is
    on file yet, says so explicitly rather than omitting the section
    (so the model doesn't assume "no allergies" when it's really "unknown").
    """
    lines = [f"Patient on file: {patient.name}."]

    if patient.medications:
        meds = "; ".join(
            f"{m.name}"
            + (f" ({m.dosage}, {m.frequency})" if m.dosage or m.frequency else "")
            + f" [{m.status}"
            + (f", prescribed {m.prescribed_date}" if m.prescribed_date else f", added {m.created_at.date()}")
            + "]"
            for m in patient.medications
        )
        lines.append(f"Medications on file (active and past): {meds}.")
    else:
        lines.append("Medications on file: none.")

    if patient.allergies:
        def _allergy_line(a):
            base = a.substance
            if a.reaction or a.severity:
                base += f" (reaction: {a.reaction}, severity: {a.severity})"
            when = f"identified {a.identified_date}" if a.identified_date else f"added {a.created_at.date()}"
            return f"{base} [{when}]"

        allergies = "; ".join(_allergy_line(a) for a in patient.allergies)
        lines.append(f"Known allergies: {allergies}.")
    else:
        lines.append("Known allergies: none on file.")

    if patient.conditions:
        def _condition_line(c):
            base = c.name
            if c.status:
                base += f" ({c.status})"
            when = f"diagnosed {c.diagnosed_date}" if c.diagnosed_date else f"added {c.created_at.date()}"
            return f"{base} [{when}]"

        conditions = "; ".join(_condition_line(c) for c in patient.conditions)
        lines.append(f"Known conditions: {conditions}.")
    else:
        lines.append("Known conditions: none on file.")

    if patient.notes:
        lines.append(f"Additional notes: {patient.notes}")

    lines.append(
        "Use this background to tailor general information (e.g. flag "
        "relevant interactions or contraindications to consider raising "
        "with a clinician) but do not treat it as exhaustive or fully "
        "verified — confirm anything critical with the patient or their "
        "provider rather than assuming this list is complete."
    )

    return "\n".join(lines)


def get_recent_history(db: Session, patient_id: int, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict[str, str]]:
    msgs = (
        db.query(models.Message)
        .filter(models.Message.patient_id == patient_id)
        .order_by(models.Message.created_at.desc())
        .limit(limit)
        .all()
    )
    msgs.reverse()  # chronological order for the model
    return [{"role": m.role, "content": m.content} for m in msgs]


def save_message(db: Session, patient_id: int, role: str, content: str) -> None:
    db.add(models.Message(patient_id=patient_id, role=role, content=content))
    db.commit()
