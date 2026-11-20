from fastapi import APIRouter, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from src.app.schemas.voice import InstructionRequest, TranscribeFlowResponse
from src.app.services.executor import ExecutionError, execute_instruction
from src.app.services.instruction_service import InstructionError, route_transcription
from src.app.services.transcription_service import TranscriptionError, transcribe_audio
from src.app.utils.language import normalize_transcription_language

MAX_AUDIO_BYTES = 25 * 1024 * 1024

router = APIRouter(tags=["transcribe"])


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    # The frontend sends JSON for manual text input and multipart audio otherwise.
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            text = InstructionRequest.model_validate(await request.json()).transcription
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON body: expected {'transcription': '...'}",
            ) from error
    else:
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing 'file' audio field.",
            )

        content = await upload.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio file.")
        if len(content) > MAX_AUDIO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio file exceeds 25 MB.",
            )

        language = normalize_transcription_language(form.get("language"))
        try:
            text = await run_in_threadpool(
                transcribe_audio,
                upload.filename or "audio.webm",
                content,
                language,
            )
        except TranscriptionError as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    text = text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No speech detected in audio.",
        )

    try:
        instruction = await run_in_threadpool(route_transcription, text)
    except InstructionError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    try:
        result = execute_instruction(instruction)
    except ExecutionError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    return TranscribeFlowResponse(transcription=text, instruction=instruction, result=result)
