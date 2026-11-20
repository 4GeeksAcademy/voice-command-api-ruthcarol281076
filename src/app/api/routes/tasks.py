from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate
from src.app.services import tasks_service
from src.app.services.tasks_service import TaskNotFoundError

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _not_found(error: TaskNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.get("", response_model=list[Task])
def get_tasks() -> list[Task]:
    return tasks_service.list_tasks()


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> Task:
    return tasks_service.create_task(title=payload.title, done=payload.done)


@router.put("/{task_id}", response_model=Task)
def replace_task(
    task_id: int,
    payload: TaskReplace,
) -> Task:
    try:
        return tasks_service.replace_task(task_id, payload.title, payload.done)
    except TaskNotFoundError as error:
        raise _not_found(error) from error


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    payload: TaskUpdate,
) -> Task:
    # Skip explicit nulls so required fields cannot be cleared.
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    try:
        return tasks_service.update_task(task_id, changes)
    except TaskNotFoundError as error:
        raise _not_found(error) from error


@router.delete("/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    try:
        tasks_service.delete_task(task_id)
    except TaskNotFoundError as error:
        raise _not_found(error) from error
    return {"detail": "Task deleted"}
