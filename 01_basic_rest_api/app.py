"""A minimal FastAPI example for teaching REST API basics.

This app is intentionally small and readable. It shows:
1. How to define request and response models.
2. How to create GET and POST routes.
3. How FastAPI validates input automatically.

Run:
    uvicorn app:app --reload --port 8000
"""

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Basic REST API Example", version="1.0.0")


class TaskCreate(BaseModel):
    """Input model for creating a new task."""

    title: str = Field(..., min_length=3, max_length=100)
    completed: bool = False


class Task(TaskCreate):
    """Stored task model returned to the client."""

    task_id: str
    created_at: str


# In-memory storage is perfect for a teaching demo.
# For production, replace this with a database.
TASKS: List[Task] = []


@app.get("/")
def root() -> dict:
    """Basic entry route so students can verify the API is running."""

    return {
        "message": "Basic REST API example is running.",
        "next_steps": [
            "GET /tasks",
            "POST /tasks",
            "GET /tasks/{task_id}",
        ],
    }


@app.get("/tasks", response_model=list[Task])
def list_tasks() -> list[Task]:
    """Return every task currently stored in memory."""

    return TASKS


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate) -> Task:
    """Create a new task from client input."""

    task = Task(
        task_id=str(uuid4()),
        title=payload.title,
        completed=payload.completed,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    TASKS.append(task)
    return task


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: str) -> Task:
    """Look up a single task by its ID."""

    for task in TASKS:
        if task.task_id == task_id:
            return task

    raise HTTPException(status_code=404, detail="Task not found")
