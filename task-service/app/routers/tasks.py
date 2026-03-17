from fastapi import APIRouter, Depends, HTTPException
import httpx

from app.schemas import TaskCreate, TaskUpdate
from app.dependencies import get_db, get_current_user
from app.crud import create_task, get_task, update_task, delete_task
from app.crud import task_serializer
from app.config import NOTIFICATION_URL, USER_SERVICE_URL


router = APIRouter(prefix="/tasks", tags=["Tasks"])


# -----------------------------
# Helper: fetch user name
# -----------------------------
async def get_user_name(user_id: str):

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{USER_SERVICE_URL}/users/{user_id}"
            )

        if resp.status_code == 200:
            return resp.json().get("name")

    except Exception:
        pass

    return None


# -----------------------------
# Get all tasks
# -----------------------------
@router.get("/")
async def get_tasks(
    db=Depends(get_db),
    user=Depends(get_current_user)
):

    tasks = []

    cursor = db.tasks.find()

    async for task in cursor:
        tasks.append(task_serializer(task))

    return tasks


# -----------------------------
# Create task
# -----------------------------
@router.post("/")
async def create_task_endpoint(
    task: TaskCreate,
    db=Depends(get_db),
    user=Depends(get_current_user)
):

    new_task = await create_task(db, task, user["id"])

    task_id = str(new_task["_id"])

    # Send notification webhook
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{NOTIFICATION_URL}/notify/task-created",
                json={
                    "task_id": task_id,
                    "assigned_to": user["id"],
                    "title": task.title
                }
            )
    except Exception:
        pass

    return {"id": task_id}


# -----------------------------
# Get single task
# -----------------------------
@router.get("/{task_id}")
async def get_task_endpoint(
    task_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user)
):

    task = await get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_serializer(task)


# -----------------------------
# Update task
# -----------------------------
@router.put("/{task_id}")
async def update_task_endpoint(
    task_id: str,
    task_update: TaskUpdate,
    db=Depends(get_db),
    user=Depends(get_current_user)
):

    updated = await update_task(
        db,
        task_id,
        task_update.dict(exclude_none=True)
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_serializer(updated)


# -----------------------------
# Delete task
# -----------------------------
@router.delete("/{task_id}")
async def delete_task_endpoint(
    task_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user)
):

    result = await delete_task(db, task_id)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task deleted"}