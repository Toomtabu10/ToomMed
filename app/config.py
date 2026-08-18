"""
Configuration for ToomMED's online Gemini LLM + local SQLite patient memory.

The SQLite database and FastAPI service remain on the user's computer.
Only the prompt/history/patient context assembled for a chat request is sent
through the configured online LLM API.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Gemini connection ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Gemini 2.5 Flash-Lite has a free API tier and is designed for low-cost,
# high-volume text tasks. Change this with GEMINI_MODEL if desired.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-3.5-flash-lite")

# --- Generation parameters ---
TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.3"))
TOP_P = float(os.getenv("MODEL_TOP_P", "0.9"))

# Keep the prompt/history reasonably small for a responsive chat experience.
NUM_CTX = int(os.getenv("MODEL_NUM_CTX", "4096"))

# --- Safety / framing ---
SYSTEM_PROMPT = (
    "You are ToomMED, a medical information assistant. "
    "Provide general, educational health information — you do not diagnose, "
    "prescribe, or replace a licensed clinician. Follow these rules in every response:\n"
    "1. If the user describes symptoms that could indicate a medical emergency "
    "(e.g. chest pain, difficulty breathing, stroke symptoms, severe bleeding, "
    "suicidal ideation), clearly tell them to seek emergency care immediately "
    "before anything else.\n"
    "2. Give general, well-established medical information and avoid definitive "
    "diagnostic claims about the specific person.\n"
    "3. Recommend confirming medical decisions with a licensed healthcare professional.\n"
    "4. If uncertain, say so rather than guessing.\n"
    "5. Do not provide specific dosing instructions for prescription-only "
    "medications; suggest confirming dosing with a pharmacist or prescriber.\n"
)

EMERGENCY_KEYWORDS = [
    "chest pain", "can't breathe", "cannot breathe", "difficulty breathing",
    "severe bleeding", "unconscious", "stroke", "suicidal", "kill myself",
    "overdose", "anaphylaxis", "seizure", "not breathing",
]

EMERGENCY_BANNER = (
    "⚠️ If this is a medical emergency, call your local emergency number "
    "(e.g. 112 / 108 in India) or go to the nearest emergency room right now. "
    "The message below is general information only and is not a substitute "
    "for emergency care.\n\n"
)
