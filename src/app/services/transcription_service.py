from groq import Groq

from src.app.core.config import get_settings
from src.app.services.groq_client import get_groq_client


class TranscriptionError(Exception):
    pass


def transcribe_audio(filename: str, content: bytes, language: str | None) -> str:
    settings = get_settings()
    client: Groq = get_groq_client()

    options: dict[str, str | float] = {"response_format": "json", "temperature": 0}
    if language:
        options["language"] = language

    try:
        result = client.audio.transcriptions.create(
            file=(filename, content),
            model=settings.groq_transcription_model,
            **options,
        )
    except Exception as error:
        raise TranscriptionError("Groq transcription failed") from error

    return result.text.strip()
