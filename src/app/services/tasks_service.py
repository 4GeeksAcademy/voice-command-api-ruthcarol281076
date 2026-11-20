from typing import Any

from src.app.schemas.voice import Task


class TaskNotFoundError(LookupError):
    def __init__(self, task_id: int) -> None:
        super().__init__(f"Task {task_id} not found")
        self.task_id = task_id


# In-memory storage shared by the tasks routes and the voice flow.
tasks: list[Task] = []
_next_task_id = 1


def _find_index(task_id: int) -> int:
    for index, task in enumerate(tasks):
        if task.id == task_id:
            return index
    raise TaskNotFoundError(task_id)


def list_tasks() -> list[Task]:
    return tasks


def create_task(title: str, done: bool = False) -> Task:
    global _next_task_id

    task = Task(id=_next_task_id, title=title, done=done)
    _next_task_id += 1
    tasks.append(task)
    return task


def replace_task(task_id: int, title: str, done: bool) -> Task:
    index = _find_index(task_id)
    task = Task(id=task_id, title=title, done=done)
    tasks[index] = task
    return task


def update_task(task_id: int, changes: dict[str, Any]) -> Task:
    index = _find_index(task_id)
    updated_task = tasks[index].model_copy(update=changes)
    tasks[index] = updated_task
    return updated_task


def delete_task(task_id: int) -> None:
    index = _find_index(task_id)
    del tasks[index]
