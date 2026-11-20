from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from src.app.schemas.voice import (
    InstructionPayload,
    TaskCreate,
    TaskReplace,
    TaskUpdate,
)
from src.app.services import tasks_service
from src.app.services.tasks_service import TaskNotFoundError


class ExecutionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _TaskIdParams(BaseModel):
    task_id: int


Handler = Callable[[dict[str, Any]], Any]

ModelT = TypeVar("ModelT", bound=BaseModel)


def _parse(model: type[ModelT], params: dict[str, Any]) -> ModelT:
    try:
        return model.model_validate(params)
    except ValidationError as error:
        raise ExecutionError(422, f"Invalid params: {error}") from error


def _list_tasks(params: dict[str, Any]) -> Any:
    return tasks_service.list_tasks()


def _create_task(params: dict[str, Any]) -> Any:
    data = _parse(TaskCreate, params)
    return tasks_service.create_task(title=data.title, done=data.done)


def _replace_task(params: dict[str, Any]) -> Any:
    task_id = _parse(_TaskIdParams, params).task_id
    data = _parse(TaskReplace, params)
    return tasks_service.replace_task(task_id, data.title, data.done)


def _update_task(params: dict[str, Any]) -> Any:
    task_id = _parse(_TaskIdParams, params).task_id
    data = _parse(TaskUpdate, params)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    return tasks_service.update_task(task_id, changes)


def _delete_task(params: dict[str, Any]) -> Any:
    task_id = _parse(_TaskIdParams, params).task_id
    tasks_service.delete_task(task_id)
    return {"detail": "Task deleted"}


HANDLERS: dict[tuple[str, str], Handler] = {
    ("GET", "/tasks"): _list_tasks,
    ("POST", "/tasks"): _create_task,
    ("PUT", "/tasks/{task_id}"): _replace_task,
    ("PATCH", "/tasks/{task_id}"): _update_task,
    ("DELETE", "/tasks/{task_id}"): _delete_task,
}


def execute_instruction(instruction: InstructionPayload) -> Any:
    handler = HANDLERS.get((instruction.method.upper(), instruction.endpoint))
    if handler is None:
        raise ExecutionError(400, f"Unsupported action: {instruction.method} {instruction.endpoint}")

    try:
        return handler(instruction.params)
    except TaskNotFoundError as error:
        raise ExecutionError(404, str(error)) from error
