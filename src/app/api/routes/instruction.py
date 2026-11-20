from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import InstructionPayload, InstructionRequest
from src.app.services.instruction_service import InstructionError, route_transcription

router = APIRouter(tags=["instruction"])


@router.post("/instruction", response_model=InstructionPayload)
def route_instruction(
    payload: InstructionRequest,
) -> InstructionPayload:
    try:
        return route_transcription(payload.transcription)
    except InstructionError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
