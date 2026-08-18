"""
FastAPI service pairing a local Ollama medical model with persistent,
per-patient memory: structured facts (medications/allergies/conditions)
plus chat history, stored in a local SQLite file.

Run:
    uvicorn app.main:app --reload --port 8000
    open http://127.0.0.1:8000/docs
"""

from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import config, models, schemas, memory
from .database import Base, engine, get_db
from .ollama_client import MedicalOllamaClient, ModelNotAvailableError

medical_client: Optional[MedicalOllamaClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global medical_client
    Base.metadata.create_all(bind=engine)  # creates patients.db tables on first run
    try:
        medical_client = MedicalOllamaClient()
    except ModelNotAvailableError as e:
        raise RuntimeError(str(e)) from e
    yield


app = FastAPI(
    title="Local Medical LLM with Patient Memory (Ollama-backed)",
    description=(
        "Runs entirely on your local machine via Ollama. Provides general "
        "medical information only - not a diagnostic or emergency service. "
        "Structured patient facts are edited only through explicit "
        "endpoints, never inferred automatically from chat."
    ),
    lifespan=lifespan,
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    """Browser-only chat UI - no curl or Swagger forms needed."""
    return FileResponse(STATIC_DIR / "index.html")


def get_patient_or_404(patient_id: int, db: Session) -> models.Patient:
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.get("/health")
def health():
    return {"status": "ok", "model": config.MODEL_NAME, "ollama_host": config.OLLAMA_HOST}


# ---------- Patients ----------

@app.post("/patients", response_model=schemas.PatientOut)
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    db_patient = models.Patient(name=patient.name, notes=patient.notes)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


@app.get("/patients", response_model=list[schemas.PatientOut])
def list_patients(db: Session = Depends(get_db)):
    return db.query(models.Patient).order_by(models.Patient.created_at.desc()).all()


@app.get("/patients/{patient_id}", response_model=schemas.PatientOut)
def read_patient(patient_id: int, db: Session = Depends(get_db)):
    return get_patient_or_404(patient_id, db)


@app.get("/patients/{patient_id}/summary", response_model=schemas.PatientSummary)
def patient_summary(patient_id: int, db: Session = Depends(get_db)):
    patient = get_patient_or_404(patient_id, db)
    message_count = db.query(models.Message).filter(models.Message.patient_id == patient_id).count()
    return schemas.PatientSummary(
        patient=patient,
        medications=patient.medications,
        allergies=patient.allergies,
        conditions=patient.conditions,
        message_count=message_count,
    )


# ---------- Structured facts (explicit CRUD only - never auto-written) ----------

@app.post("/patients/{patient_id}/medications", response_model=schemas.MedicationOut)
def add_medication(patient_id: int, med: schemas.MedicationCreate, db: Session = Depends(get_db)):
    get_patient_or_404(patient_id, db)
    db_med = models.Medication(patient_id=patient_id, **med.model_dump())
    db.add(db_med)
    db.commit()
    db.refresh(db_med)
    return db_med


@app.post("/patients/{patient_id}/allergies", response_model=schemas.AllergyOut)
def add_allergy(patient_id: int, allergy: schemas.AllergyCreate, db: Session = Depends(get_db)):
    get_patient_or_404(patient_id, db)
    db_allergy = models.Allergy(patient_id=patient_id, **allergy.model_dump())
    db.add(db_allergy)
    db.commit()
    db.refresh(db_allergy)
    return db_allergy


@app.post("/patients/{patient_id}/conditions", response_model=schemas.ConditionOut)
def add_condition(patient_id: int, condition: schemas.ConditionCreate, db: Session = Depends(get_db)):
    get_patient_or_404(patient_id, db)
    db_condition = models.Condition(patient_id=patient_id, **condition.model_dump())
    db.add(db_condition)
    db.commit()
    db.refresh(db_condition)
    return db_condition


@app.delete("/medications/{medication_id}")
def delete_medication(medication_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.Medication).filter(models.Medication.id == medication_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Medication not found")
    db.delete(obj)
    db.commit()
    return {"deleted": medication_id}


@app.delete("/allergies/{allergy_id}")
def delete_allergy(allergy_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.Allergy).filter(models.Allergy.id == allergy_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Allergy not found")
    db.delete(obj)
    db.commit()
    return {"deleted": allergy_id}


@app.delete("/conditions/{condition_id}")
def delete_condition(condition_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.Condition).filter(models.Condition.id == condition_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Condition not found")
    db.delete(obj)
    db.commit()
    return {"deleted": condition_id}


# ---------- Chat (reads structured facts + history, writes only to the message log) ----------

@app.get("/patients/{patient_id}/history", response_model=list[schemas.MessageOut])
def chat_history(patient_id: int, db: Session = Depends(get_db)):
    get_patient_or_404(patient_id, db)
    return (
        db.query(models.Message)
        .filter(models.Message.patient_id == patient_id)
        .order_by(models.Message.created_at.asc())
        .all()
    )


@app.post("/patients/{patient_id}/chat", response_model=None)
def chat(patient_id: int, req: schemas.ChatRequest, db: Session = Depends(get_db)):
    if medical_client is None:
        raise HTTPException(status_code=503, detail="Model client not initialized")

    patient = get_patient_or_404(patient_id, db)
    patient_context = memory.build_patient_context(patient)
    history = memory.get_recent_history(db, patient_id)

    # Log the user's message immediately, before generating a reply, so it
    # isn't lost if the model call fails.
    memory.save_message(db, patient_id, "user", req.message)

    if req.stream:
        def token_stream():
            full_reply = ""
            for chunk in medical_client.chat_stream(req.message, history, patient_context):
                full_reply += chunk
                yield chunk
            memory.save_message(db, patient_id, "assistant", full_reply)
        return StreamingResponse(token_stream(), media_type="text/plain")

    reply = medical_client.chat(req.message, history, patient_context)
    memory.save_message(db, patient_id, "assistant", reply)
    return schemas.ChatResponse(reply=reply, model=medical_client.model)
