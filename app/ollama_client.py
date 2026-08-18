"""Gemini API client for ToomMED.

The patient database stays local in SQLite/FastAPI. This module only sends
the assembled chat request to Google's Gemini API and streams the response
back to the local frontend.
"""

from typing import Iterator, List, Dict

from google import genai
from google.genai import types

from . import config


class ModelNotAvailableError(RuntimeError):
    """Raised when the online Gemini client cannot be configured."""


def contains_emergency_language(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in config.EMERGENCY_KEYWORDS)


class MedicalGeminiClient:
    """Wrap Gemini with ToomMED's safety framing and patient context."""

    def __init__(self, model: str | None = None):
        if not config.GEMINI_API_KEY:
            raise ModelNotAvailableError(
                "GEMINI_API_KEY is not configured. Create a Gemini API key "
                "in Google AI Studio and put GEMINI_API_KEY=... in your .env file."
            )

        self.model = model or config.GEMINI_MODEL
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    def _build_contents(
        self,
        history: List[Dict[str, str]],
        user_message: str,
        patient_context: str | None = None,
    ) -> tuple[str, list[dict]]:
        system_content = config.SYSTEM_PROMPT
        if patient_context:
            system_content += "\n\nLOCAL PATIENT CONTEXT:\n" + patient_context

        contents: list[dict] = []
        for item in history:
            role = item.get("role", "user")
            # Gemini uses "model" rather than "assistant".
            if role == "assistant":
                role = "model"
            if role not in {"user", "model"}:
                continue
            contents.append({
                "role": role,
                "parts": [{"text": item.get("content", "")}],
            })

        contents.append({
            "role": "user",
            "parts": [{"text": user_message}],
        })

        return system_content, contents

    def _config(self, system_content: str) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system_content,
            temperature=config.TEMPERATURE,
            top_p=config.TOP_P,
            max_output_tokens=1024,
        )

    def chat(
        self,
        user_message: str,
        history: List[Dict[str, str]] | None = None,
        patient_context: str | None = None,
    ) -> str:
        history = history or []
        system_content, contents = self._build_contents(
            history, user_message, patient_context
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=self._config(system_content),
        )
        reply = response.text or "I couldn't generate a response. Please try again."

        if contains_emergency_language(user_message):
            reply = config.EMERGENCY_BANNER + reply

        return reply

    def chat_stream(
        self,
        user_message: str,
        history: List[Dict[str, str]] | None = None,
        patient_context: str | None = None,
    ) -> Iterator[str]:
        """Stream Gemini text chunks as soon as they are generated."""
        history = history or []
        system_content, contents = self._build_contents(
            history, user_message, patient_context
        )

        if contains_emergency_language(user_message):
            yield config.EMERGENCY_BANNER

        stream = self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=self._config(system_content),
        )

        for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yield text
