from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId


# -----------------------------
# Create Task
# -----------------------------
async def create_task(db, task_data, user_id):

    task = {

        "title": task_data.title,
        "description": task_data.description,

        "status": "pending",

        "priority": task_data.priority.value if hasattr(task_data.priority, "value") else task_data.priority,

        "assigned_to": None,

        "created_by": ObjectId(user_id),

        "created_at": datetime.utcnow(),

        "updated_at": datetime.utcnow(),

        "due_date": task_data.due_date,

        # new field
        "completed_at": None,

        "tags": task_data.tags
    }

    result = await db.tasks.insert_one(task)

    task["_id"] = result.inserted_id

    return task


# -----------------------------
# Serializer
# -----------------------------
def task_serializer(task) -> dict:
    return {
        "id": str(task["_id"]),
        "title": task["title"],
        "description": task["description"],
        "status": task["status"],
        "priority": task["priority"],
        "assigned_to": str(task["assigned_to"]) if task.get("assigned_to") else None,
        "created_by": str(task["created_by"]),
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
        "due_date": task["due_date"],

        # added field
        "completed_at": task.get("completed_at"),

        "tags": task["tags"]
    }


# -----------------------------
# Get Single Task
# -----------------------------
async def get_task(db, task_id):

    try:
        task = await db.tasks.find_one({"_id": ObjectId(task_id)})
        return task
    except InvalidId:
        return None


# -----------------------------
# Get All Tasks
# -----------------------------
async def get_tasks(db):

    tasks = []

    cursor = db.tasks.find()

    async for task in cursor:

        task["_id"] = str(task["_id"])

        tasks.append(task)

    return tasks


# -----------------------------
# Update Task
# -----------------------------
async def update_task(db, task_id, updates):

    try:

        updates["updated_at"] = datetime.utcnow()

        # if status becomes completed → set completed_at
        if updates.get("status") == "completed":
            updates["completed_at"] = datetime.utcnow()

        await db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": updates}
        )

        task = await db.tasks.find_one({"_id": ObjectId(task_id)})

        return task

    except InvalidId:
        return None


# -----------------------------
# Delete Task
# -----------------------------
async def delete_task(db, task_id):

    try:

        result = await db.tasks.delete_one(
            {"_id": ObjectId(task_id)}
        )

        return result

    except InvalidId:
        return None