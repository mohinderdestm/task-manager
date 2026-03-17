from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models import TaskPriority, TaskStatus


class TaskCreate(BaseModel):

    title: str = Field(..., min_length=1, max_length=200)

    description: Optional[str] = None

    priority: TaskPriority = TaskPriority.medium

    due_date: Optional[datetime] = None

    tags: List[str] = []


class TaskUpdate(BaseModel):

    title: Optional[str] = None

    description: Optional[str] = None

    status: Optional[TaskStatus] = None

    priority: Optional[TaskPriority] = None

    due_date: Optional[datetime] = None

    tags: Optional[List[str]] = None


class TaskResponse(BaseModel):

    id: str

    title: str

    description: Optional[str]

    status: TaskStatus

    priority: TaskPriority

    assigned_to: Optional[str]

    created_by: str

    created_at: datetime

    updated_at: datetime

    due_date: Optional[datetime]

    completed_at: Optional[datetime]  # ← added field

    tags: List[str]

    user_name: Optional[str]


class TaskListResponse(BaseModel):

    total_count: int

    tasks: List[TaskResponse]