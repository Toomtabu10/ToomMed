"""
Terminal chat with persistent, per-patient memory (SQLite-backed).

Run:
    python cli.py

On start, pick or create a patient. Structured facts (medications,
allergies, conditions) are managed via the FastAPI endpoints /
Swagger UI (uvicorn app.main:app) - this CLI is for chatting, not
editing the record.
"""

from app.database import Base, engine, SessionLocal
from app import models, memory
from app.ollama_client import MedicalOllamaClient, ModelNotAvailableError
from app import config


def pick_or_create_patient(db):
    patients = db.query(models.Patient).all()
    if patients:
        print("\nExisting patients:")
        for p in patients:
            print(f"  [{p.id}] {p.name}")
    print("Enter a patient ID to continue, or a new name to create one.")
    choice = input("> ").strip()

    if choice.isdigit():
        patient = db.query(models.Patient).filter(models.Patient.id == int(choice)).first()
        if patient:
            return patient
        print("No patient with that ID, creating a new one instead.")

    patient = models.Patient(name=choice or "Unnamed patient")
    db.add(patient)
    db.commit()
    db.refresh(patient)
    print(f"Created patient [{patient.id}] {patient.name}")
    return patient


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print(f"Loading model '{config.MODEL_NAME}' via Ollama at {config.OLLAMA_HOST} ...")
    try:
        client = MedicalOllamaClient()
    except ModelNotAvailableError as e:
        print(f"\n{e}\n")
        return

    patient = pick_or_create_patient(db)
    patient_context = memory.build_patient_context(patient)
    history = memory.get_recent_history(db, patient.id)

    print(f"\nChatting as patient: {patient.name} (id={patient.id})")
    print("This is general medical information only - not a diagnosis.")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        memory.save_message(db, patient.id, "user", user_input)

        print("Assistant: ", end="", flush=True)
        full_reply = ""
        for chunk in client.chat_stream(user_input, history, patient_context):
            print(chunk, end="", flush=True)
            full_reply += chunk
        print("\n")

        memory.save_message(db, patient.id, "assistant", full_reply)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": full_reply})


if __name__ == "__main__":
    main()
