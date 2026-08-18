"""
Configuration for the local Ollama + medical LLM pairing.

Everything here is overridable via environment variables so the same
code runs unchanged across different machines / models.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Ollama connection ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# --- Model selection ---
# Pull one of these first with `ollama pull <name>`, e.g.:
#   ollama pull meditron          (7B/70B, EPFL-LLM, medical domain fine-tune)
#   ollama pull medllama2         (Llama2 fine-tuned on medical Q&A)
#   ollama pull biomistral        (Mistral fine-tuned on biomedical text)
# Any general-purpose Ollama model (llama3.1, qwen2.5, etc.) also works,
# just with less domain specialization.
MODEL_NAME = os.getenv("OLLAMA_MEDICAL_MODEL", "meditron")

# --- Generation parameters ---
TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.3"))  # lower = more consistent/less creative
TOP_P = float(os.getenv("MODEL_TOP_P", "0.9"))
NUM_CTX = int(os.getenv("MODEL_NUM_CTX", "4096"))  # context window, raise if the model supports more

# --- Safety / framing ---
# This system prompt is prepended to every conversation. It keeps the
# model's output framed as general information rather than a diagnosis,
# and asks it to flag emergencies and cite uncertainty instead of
# guessing confidently.
SYSTEM_PROMPT = (
    "You are a medical information assistant running entirely on the user's "
    "local machine. You provide general, educational health information — "
    "you do not diagnose, prescribe, or replace a licensed clinician. "
    "Follow these rules in every response:\n"
    "1. If the user describes symptoms that could indicate a medical "
    "emergency (e.g. chest pain, difficulty breathing, stroke symptoms, "
    "severe bleeding, suicidal ideation), tell them clearly to seek "
    "emergency care immediately (call local emergency services), before "
    "anything else.\n"
    "2. Give general, well-established medical information and explain "
    "your reasoning, but avoid definitive diagnostic claims about the "
    "specific person you're talking to.\n"
    "3. Recommend confirming any medical decision with a licensed "
    "healthcare professional.\n"
    "4. If you are uncertain, say so explicitly rather than guessing.\n"
    "5. Do not provide specific dosing instructions for prescription-only "
    "medications; suggest the user confirm dosing with a pharmacist or "
    "prescriber.\n"
)

EMERGENCY_KEYWORDS = [
    "chest pain", "can't breathe", "cannot breathe", "difficulty breathing",
    "severe bleeding", "unconscious", "stroke", "suicidal", "kill myself",
    "overdose", "anaphylaxis", "seizure", "not breathing",
]

EMERGENCY_BANNER = (
    "⚠️ If this is a medical emergency, call your local emergency number "
    "(e.g. 911 / 112 / 108) or go to the nearest emergency room right now. "
    "The message below is general information only and is not a substitute "
    "for emergency care.\n\n"
)
