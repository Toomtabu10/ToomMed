"""
Thin wrapper around the local Ollama runtime for the medical model.

Ollama itself does the model serving (it must be installed and running
locally — see README). This module just handles:
  - building the conversation with a fixed safety system prompt
  - a lightweight emergency-keyword pre-check
  - streaming or single-shot chat calls
  - a startup check that the requested model is actually pulled
"""

from typing import Iterator, List, Dict
import ollama

from . import config


class ModelNotAvailableError(RuntimeError):
    """Raised when the configured model isn't pulled locally yet."""


def ensure_model_available(client: "ollama.Client") -> None:
    models = client.list().get("models", [])
    names = {m.get("model", m.get("name", "")) for m in models}
    # Ollama sometimes reports "meditron:latest" vs "meditron" — normalize.
    normalized = {n.split(":")[0] for n in names}
    if config.MODEL_NAME.split(":")[0] not in normalized:
        raise ModelNotAvailableError(
            f"Model '{config.MODEL_NAME}' is not pulled locally.\n"
            f"Run: ollama pull {config.MODEL_NAME}\n"
            f"Available locally: {sorted(names) or 'none'}"
        )


def contains_emergency_language(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in config.EMERGENCY_KEYWORDS)


class MedicalOllamaClient:
    """Wraps an Ollama chat session with a persistent medical-safety framing."""

    def __init__(self, model: str | None = None, host: str | None = None):
        self.model = model or config.MODEL_NAME
        self.client = ollama.Client(host=host or config.OLLAMA_HOST)
        ensure_model_available(self.client)

    def _build_messages(
        self,
        history: List[Dict[str, str]],
        user_message: str,
        patient_context: str | None = None,
    ) -> List[Dict[str, str]]:
        system_content = config.SYSTEM_PROMPT
        if patient_context:
            system_content += "\n\n" + patient_context
        messages = [{"role": "system", "content": system_content}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages

    def chat(
        self,
        user_message: str,
        history: List[Dict[str, str]] | None = None,
        patient_context: str | None = None,
    ) -> str:
        """Single-shot (non-streaming) chat call. Returns the full reply text."""
        history = history or []
        messages = self._build_messages(history, user_message, patient_context)

        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": config.TEMPERATURE,
                "top_p": config.TOP_P,
                "num_ctx": config.NUM_CTX,
            },
        )
        reply = response["message"]["content"]

        if contains_emergency_language(user_message):
            reply = config.EMERGENCY_BANNER + reply

        return reply

    def chat_stream(
        self,
        user_message: str,
        history: List[Dict[str, str]] | None = None,
        patient_context: str | None = None,
    ) -> Iterator[str]:
        """Streaming chat call. Yields text chunks as they arrive."""
        history = history or []
        messages = self._build_messages(history, user_message, patient_context)

        if contains_emergency_language(user_message):
            yield config.EMERGENCY_BANNER

        stream = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": config.TEMPERATURE,
                "top_p": config.TOP_P,
                "num_ctx": config.NUM_CTX,
            },
            stream=True,
        )
        for chunk in stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content
