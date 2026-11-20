import json
import re

from pydantic import ValidationError

from src.app.core.config import get_settings
from src.app.schemas.voice import InstructionPayload
from src.app.services.groq_client import get_groq_client

# Routes the LLM may select. Anything outside this set is rejected.
ALLOWED_ROUTES: dict[tuple[str, str], str] = {
    ("GET", "/tasks"): "List all tasks. params: {}",
    ("POST", "/tasks"): "Create a task. params: {title: string, done?: boolean}",
    ("PUT", "/tasks/{task_id}"): "Replace a task. params: {task_id: integer, title: string, done: boolean}",
    ("PATCH", "/tasks/{task_id}"): "Update a task. params: {task_id: integer, title?: string, done?: boolean}",
    ("DELETE", "/tasks/{task_id}"): "Delete a task. params: {task_id: integer}",
}

SYSTEM_PROMPT = (
    "You route voice commands for a task list API. "
    "Given the user's transcription, choose exactly one route from the list below "
    "and reply ONLY with a JSON object of the form "
    '{"endpoint": string, "method": string, "params": object}.\n\n'
    "Available routes:\n"
    + "\n".join(
        f"- {method} {endpoint}: {description}"
        for (method, endpoint), description in ALLOWED_ROUTES.items()
    )
    + "\n\nUse the exact endpoint template (e.g. /tasks/{task_id}) and put path values in params."
)


CONCRETE_TASK_PATH = re.compile(r"^/tasks/(\d+)$")


class InstructionError(Exception):
    pass


def _normalize_endpoint(endpoint: str, params: dict) -> tuple[str, dict]:
    # The model may return a concrete path such as /tasks/1 instead of the template.
    match = CONCRETE_TASK_PATH.match(endpoint)
    if match is None:
        return endpoint, params
    return "/tasks/{task_id}", {**params, "task_id": int(match.group(1))}


def route_transcription(transcription: str) -> InstructionPayload:
    settings = get_settings()
    client = get_groq_client()

    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcription},
            ],
        )
    except Exception as error:
        raise InstructionError("Groq request failed") from error

    content = completion.choices[0].message.content or ""
    try:
        payload = InstructionPayload.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValidationError) as error:
        raise InstructionError("Groq returned an invalid routing payload") from error

    endpoint, params = _normalize_endpoint(payload.endpoint, payload.params)
    if (payload.method.upper(), endpoint) not in ALLOWED_ROUTES:
        raise InstructionError(
            f"Groq selected an unsupported route: {payload.method} {payload.endpoint}"
        )

    return InstructionPayload(
        endpoint=endpoint,
        method=payload.method.upper(),
        params=params,
    )
