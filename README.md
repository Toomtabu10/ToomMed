# Local Medical LLM — Ollama + Python

A small Python project that pairs [Ollama](https://ollama.com) (local model
runtime) with a medical-domain LLM, wrapped in:

- a **CLI** (`cli.py`) for quick terminal chat, and
- a **FastAPI service** (`app/main.py`) exposing a `/chat` HTTP endpoint.

Everything — the model weights and inference — runs on your machine. No data
leaves the local machine, no API key or cloud account required.

> **Not a medical device.** This provides general, educational health
> information only. It does not diagnose, prescribe, or replace a licensed
> clinician. See the safety notes at the bottom.

## 1. Install Ollama

Download and install from https://ollama.com/download for your OS
(Windows, macOS, Linux). This gives you the `ollama` command and a local
background service that serves models at `http://localhost:11434`.

Verify it's running:

```bash
ollama --version
```

## 2. Pull a medical model

Any of these work out of the box with this project (pick one based on your
machine's RAM/VRAM — 7B models need roughly 8GB+ RAM for CPU inference,
70B variants need a serious GPU):

```bash
ollama pull meditron       # EPFL-LLM, medical-domain fine-tune (7B or 70B)
# or
ollama pull medllama2      # Llama2 fine-tuned on medical Q&A
# or
ollama pull biomistral     # Mistral fine-tuned on biomedical literature
```

You can also point this project at a general-purpose model (e.g.
`ollama pull llama3.1`) if a medical-specific model isn't available for your
platform — it'll work, just with less domain specialization.

Test it directly first:

```bash
ollama run meditron "What are the general symptoms of dehydration?"
```

## 3. Set up the Python project

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # adjust OLLAMA_MEDICAL_MODEL if needed
```

## 4. Run it

**Option A — browser only, no terminal commands after this point:**

```bash
uvicorn app.main:app --reload --port 8000
```

Then open **`http://127.0.0.1:8000/`** — a full chat UI: create/select a
patient in the sidebar, add medications/allergies/conditions with the
forms, and chat in the main panel. Everything (patient creation, facts,
chat, history) happens through that one page.

**Option B — terminal chat:**

```bash
python cli.py
```

**Option C — raw API (Swagger docs or curl):**

Open `http://127.0.0.1:8000/docs` for interactive Swagger UI, or:

```bash
curl -X POST http://127.0.0.1:8000/patients/1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What lifestyle changes help manage mild hypertension?"}'
```

For streaming responses, pass `"stream": true` in the request body — the
response comes back as a plain-text stream instead of one JSON blob (the
browser UI always uses streaming).

## Project structure

```
ollama-medical-assistant/
  app/
    __init__.py
    config.py          # model name, generation params, safety system prompt
    database.py         # SQLite engine/session (patients.db, created on first run)
    models.py           # Patient, Medication, Allergy, Condition, Message tables
    schemas.py           # Pydantic request/response models
    memory.py             # builds model context from structured facts + recent chat
    ollama_client.py    # wraps ollama.Client, adds safety framing + emergency check
    main.py             # FastAPI app: patients, facts, chat, history
  cli.py                # terminal chat with patient selection, no server needed
  requirements.txt
  .env.example
  README.md
```

## Patient memory

There are two kinds of memory here, kept deliberately separate:

1. **Chat history** — every message is logged to `messages` in `patients.db`,
   scoped to a patient. The 20 most recent messages are replayed into the
   model's context on every `/chat` call, so conversations pick up where
   they left off across restarts.
2. **Structured facts** — medications, allergies, and conditions, each in
   their own table. These are **only ever changed through their explicit
   endpoints** (`POST /patients/{id}/medications`, etc.) — the chat endpoint
   reads them into context but never writes to them. This is intentional:
   letting the model infer and silently save something like "patient
   mentioned an allergy" from freeform text is how a hallucinated fact ends
   up permanently in the record. A human (or a separate, explicitly-invoked
   extraction step you control) should be the one adding structured facts.

### Typical flow

```bash
# 1. create a patient
curl -X POST http://127.0.0.1:8000/patients \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Doe"}'
# -> {"id": 1, "name": "Jane Doe", ...}

# 2. add structured facts
curl -X POST http://127.0.0.1:8000/patients/1/medications \
  -H "Content-Type: application/json" \
  -d '{"name": "Lisinopril", "dosage": "10mg", "frequency": "once daily"}'

curl -X POST http://127.0.0.1:8000/patients/1/allergies \
  -H "Content-Type: application/json" \
  -d '{"substance": "Penicillin", "reaction": "rash", "severity": "moderate"}'

# 3. chat - the model automatically sees the facts above plus prior messages
curl -X POST http://127.0.0.1:8000/patients/1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Any interactions I should ask my doctor about?"}'

# 4. view the record / full chat log
curl http://127.0.0.1:8000/patients/1/summary
curl http://127.0.0.1:8000/patients/1/history
```

The CLI (`python cli.py`) does the same thing interactively — it lists or
creates patients, then chats with full memory, but structured facts still
need to go through the API/Swagger UI (`/docs`), not the CLI.

## How the safety framing works

- **`config.SYSTEM_PROMPT`** is prepended to every conversation, instructing
  the model to give general information (not a diagnosis), flag emergencies
  first, avoid confident guessing, and avoid specific prescription dosing.
- **`contains_emergency_language()`** does a lightweight keyword pre-check on
  the user's message (chest pain, difficulty breathing, suicidal ideation,
  etc.) and prepends an emergency-services banner to the reply *before* the
  model's own text, regardless of what the model says.
- This is a basic safeguard, not a clinical safety system — see limitations
  below.

## Swapping models or running multiple

Change `OLLAMA_MEDICAL_MODEL` in `.env`, or override per-instance:

```python
from app.ollama_client import MedicalOllamaClient
client = MedicalOllamaClient(model="biomistral")
```

You can run several models side by side in Ollama and switch between them
per-request by instantiating separate `MedicalOllamaClient` objects.

## Limitations & responsible use

- **No medical model, however fine-tuned, should be used for actual
  diagnosis or treatment decisions.** These models are trained on medical
  text but can still produce confidently wrong answers.
- The emergency keyword list is intentionally simple and will miss phrasing
  it doesn't recognize — it's a basic safety net, not a substitute for
  actually calling emergency services when needed.
- If you deploy this beyond personal/local use (e.g. for other people to
  use), consider: logging/audit trails, rate limiting, more rigorous
  emergency detection, and — depending on your jurisdiction and use case —
  whether regulatory requirements for clinical decision-support software
  apply to you.
- Model outputs are not covered by any medical liability protections; treat
  this as an information/research tool, not a clinical one.
