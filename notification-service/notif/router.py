from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime
from typing import Optional
from bson import ObjectId

from database import notifications_collection, tasks_collection, users_collection
from models import (
    NotifyTaskRequest, NotificationStatus, NotificationType,
    BulkNotifyRequest, NotifyUserRequest, TaskCreatedWebhook,
    TaskUpdatedWebhook, EmailWithAttachmentRequest
)
from utils import build_email_content, send_email

from notif.dependencies import get_current_user
# from notif.queue import notification_queue

# Celery task
from tasks import send_email_task


router = APIRouter(prefix="/notify", tags=["Notifications"])


def serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


def resolve_user_name(db_user: dict) -> str:
    return (
        db_user.get("name")
        or db_user.get("profile", {}).get("name")
        or db_user.get("username")
        or "User"
    )

async def build_and_queue(
    task_id: str,
    user_id: str,
    recipient_email: str,
    user_name: str,
    notification_type: NotificationType,
    task: dict
) -> str:
    subject, html_body = build_email_content(notification_type, task, user_name)
 
    doc = {
        "task_id": task_id,
        "user_id": user_id,
        "recipient_email": recipient_email,
        "notification_type": notification_type,
        "status": NotificationStatus.PENDING,
        "subject": subject,
        "body": html_body,
        "retry_count": 0,
        "error_message": None,
        "created_at": datetime.utcnow(),
        "sent_at": None,
        "read_at": None
    }
 
    result = await notifications_collection.insert_one(doc)
    notification_id = str(result.inserted_id)
    send_email_task.delay(notification_id)
    return notification_id

# ─────────────────────────────────────────────────────────────────────────────
# POST /notify/email-with-attachment
# Called by report-service to send emails with PDF attachments
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/email-with-attachment", status_code=status.HTTP_202_ACCEPTED)
async def send_email_with_attachment(payload: EmailWithAttachmentRequest):

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;padding:20px;
                border:1px solid #e0e0e0;border-radius:8px">
        <h2 style="color:#4A90D9">{payload.subject}</h2>
        <p>{payload.message}</p>
        <p>Please find your report attached to this email.</p>
        <p style="color:#888;font-size:12px">— Task Manager System</p>
    </div>
    """

    doc = {
        "task_id":             None,
        "user_id":             None,
        "recipient_email":     payload.recipient_email,
        "notification_type":   "salary_report",
        "status":              NotificationStatus.PENDING,
        "subject":             payload.subject,
        "body":                html_body,
        "attachment_base64":   payload.attachment_base64,
        "attachment_filename": payload.attachment_filename,
        "attachment_type":     payload.attachment_type,
        "retry_count":         0,
        "error_message":       None,
        "created_at":          datetime.utcnow(),
        "sent_at":             None
    }

    result = await notifications_collection.insert_one(doc)
    notification_id = str(result.inserted_id)
    send_email_task.delay(notification_id)

    return {
        "message": "Email with attachment queued successfully",
        "notification_id": notification_id,
        "status": NotificationStatus.PENDING,
        "recipient_email": payload.recipient_email
    }

# ─────────────────────────────────────────────────────────────────────────────
# Webhook: POST /notify/task-created
# Called by task-service automatically on task creation — no auth required
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/task-created", status_code=status.HTTP_202_ACCEPTED)
async def task_created_webhook(payload: TaskCreatedWebhook):

    user_id = payload.assigned_to
    user_name = "User"
    recipient_email = None

    try:
        db_user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if db_user:
            recipient_email = db_user.get("email")
            user_name = resolve_user_name(db_user)   # handles profile.name
    except Exception:
        pass

    if not recipient_email:
        print(f"⚠️  No email found for user_id={user_id}, skipping notification.")
        return {"message": "No email on record for user, notification skipped"}

    task = {"_id": payload.task_id, "title": payload.title}
    subject, html_body = build_email_content(NotificationType.TASK_ASSIGNED, task, user_name)

    doc = {
        "task_id": payload.task_id,
        "user_id": user_id,
        "recipient_email": recipient_email,
        "notification_type": NotificationType.TASK_ASSIGNED,
        "status": NotificationStatus.PENDING,
        "subject": subject,
        "body": html_body,
        "retry_count": 0,
        "error_message": None,
        "created_at": datetime.utcnow(),
        "sent_at": None
    }

    result = await notifications_collection.insert_one(doc)
    notification_id = str(result.inserted_id)
    send_email_task.delay(notification_id)

    return {
        "message": "Notification queued successfully",
        "notification_id": notification_id,
        "status": NotificationStatus.QUEUED,
        "recipient_email": recipient_email
    }

# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK: POST /notify/task-updated/{task_id}
# Called by task-service on task update — no auth required
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/task-updated/{task_id}", status_code=status.HTTP_202_ACCEPTED)
async def task_updated_webhook(task_id: str, payload: TaskUpdatedWebhook):
 
    user_id = payload.assigned_to
    user_name = "User"
    recipient_email = None
 
    try:
        db_user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if db_user:
            recipient_email = db_user.get("email")
            user_name = resolve_user_name(db_user)
    except Exception:
        pass
 
    if not recipient_email:
        print(f"⚠️  No email found for user_id={user_id}, skipping notification.")
        return {"message": "No email on record for user, notification skipped"}
 
    # Pick the right notification type based on the new status
    if payload.status == "completed":
        notif_type = NotificationType.TASK_COMPLETED
    elif payload.status == "cancelled":
        notif_type = NotificationType.TASK_DELETED
    else:
        notif_type = NotificationType.TASK_UPDATED
 
    task = {"_id": payload.task_id, "title": payload.title}
    notification_id = await build_and_queue(
        task_id, user_id, recipient_email, user_name, notif_type, task
    )
 
    return {
        "message": "Notification queued successfully",
        "notification_id": notification_id,
        "status": NotificationStatus.QUEUED,
        "recipient_email": recipient_email
    }


# ─────────────────────────────────────────────────────────────────────────────
# Manual trigger: POST /notify/task/{task_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/task/{task_id}", status_code=status.HTTP_202_ACCEPTED)
async def notify_task(task_id: str, request: NotifyTaskRequest, user=Depends(get_current_user)):

    try:
        task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
    except Exception:
        task = None
    task = task or {"_id": task_id, "title": f"Task {task_id}", "due_date": "N/A"}

    recipient_email = request.recipient_email
    user_name = "User"
    user_id = request.recipient_user_id or user.get("user_id", "")

    if not recipient_email:
        try:
            db_user = await users_collection.find_one({"_id": ObjectId(user_id)})
            if db_user:
                recipient_email = db_user.get("email")
                user_name = resolve_user_name(db_user)   # handles profile.name
        except Exception:
            pass

    if not recipient_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipient email or user ID is required"
        )

    subject, html_body = build_email_content(request.notification_type, task, user_name)

    doc = {
        "task_id": task_id,
        "user_id": user_id,
        "recipient_email": recipient_email,
        "notification_type": request.notification_type,
        "status": NotificationStatus.PENDING,
        "subject": subject,
        "body": html_body,
        "retry_count": 0,
        "error_message": None,
        "created_at": datetime.utcnow(),
        "sent_at": None
    }

    result = await notifications_collection.insert_one(doc)
    notification_id = str(result.inserted_id)
    send_email_task.delay(notification_id)

    return {
        "message": "Notification queued successfully",
        "notification_id": notification_id,
        "status": NotificationStatus.QUEUED,
        "recipient_email": recipient_email
    }

# ─────────────────────────────────────────────────────────────────────────────
# POST /notify/overdue
# Scans tasks collection for overdue tasks and notifies assigned users
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/overdue", status_code=status.HTTP_202_ACCEPTED)
async def notify_overdue_tasks(user=Depends(get_current_user)):
 
    now = datetime.utcnow()
    queued_ids = []
    skipped = 0
 
    cursor = tasks_collection.find({
        "due_date": {"$lt": now},
        "status": {"$nin": ["completed", "cancelled"]}
    })
 
    async for task in cursor:
        task_id = str(task["_id"])
 
        user_obj_id = task.get("assigned_to") or task.get("created_by")
        if not user_obj_id:
            skipped += 1
            continue
 
        try:
            db_user = await users_collection.find_one({"_id": user_obj_id})
        except Exception:
            skipped += 1
            continue
 
        if not db_user or not db_user.get("email"):
            skipped += 1
            continue
 
        recipient_email = db_user["email"]
        user_name = resolve_user_name(db_user)
 
        task_dict = {"_id": task_id, "title": task.get("title", f"Task {task_id}")}
        notification_id = await build_and_queue(
            task_id, str(user_obj_id), recipient_email,
            user_name, NotificationType.TASK_OVERDUE, task_dict
        )
        queued_ids.append(notification_id)
 
    return {
        "message": "Overdue notifications queued",
        "queued_count": len(queued_ids),
        "skipped_count": skipped,
        "notification_ids": queued_ids
    }

# ─────────────────────────────────────────────────────────────────────────────
# POST /notify/retry/{notification_id}
# Manually retry a failed notification
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/retry/{notification_id}", status_code=status.HTTP_202_ACCEPTED)
async def retry_notification(notification_id: str, user=Depends(get_current_user)):
 
    try:
        doc = await notifications_collection.find_one({"_id": ObjectId(notification_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID")
 
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
 
    if doc["status"] != NotificationStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only FAILED notifications can be retried. Current status: {doc['status']}"
        )
 
    # Reset to PENDING and re-enqueue
    await notifications_collection.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {
            "status": NotificationStatus.PENDING,
            "retry_count": 0,
            "error_message": None
        }}
    )
 
    send_email_task.delay(notification_id)
 
    return {
        "message": "Notification re-queued for retry",
        "notification_id": notification_id,
        "status": NotificationStatus.PENDING
    }
# ─────────────────────────────────────────────────────────────────────────────
# PATCH /notify/{notification_id}/read
# Mark a notification as read
# ─────────────────────────────────────────────────────────────────────────────
@router.patch("/{notification_id}/read")
async def mark_notification_read(notification_id: str, user=Depends(get_current_user)):
 
    try:
        doc = await notifications_collection.find_one({"_id": ObjectId(notification_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID")
 
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
 
    if doc.get("read_at"):
        return {"message": "Already marked as read", "read_at": doc["read_at"]}
 
    read_at = datetime.utcnow()
    await notifications_collection.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"read_at": read_at}}
    )
 
    return {
        "message": "Notification marked as read",
        "notification_id": notification_id,
        "read_at": read_at
    }

# ─────────────────────────────────────────────────────────────────────────────
# GET /notify/stats
# Aggregated counts by status and notification type
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/stats")
async def get_notification_stats(user=Depends(get_current_user)):
 
    # Count by status
    status_counts = {}
    for s in NotificationStatus:
        status_counts[s.value] = await notifications_collection.count_documents({"status": s.value})
 
    # Count by notification type
    type_counts = {}
    for t in NotificationType:
        type_counts[t.value] = await notifications_collection.count_documents({"notification_type": t.value})
 
    total = await notifications_collection.count_documents({})
    unread = await notifications_collection.count_documents({"read_at": None, "status": NotificationStatus.SENT})
 
    return {
        "total": total,
        "unread": unread,
        "by_status": status_counts,
        "by_type": type_counts
    }

# ─────────────────────────────────────────────────────────────────────────────
# GET /notify/user/{user_id}/feed
# All notifications for a specific user — for frontend bell icon / feed
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/user/{user_id}/feed")
async def get_user_notification_feed(
    user_id: str,
    limit: int = 20,
    skip: int = 0,
    unread_only: bool = False,
    user=Depends(get_current_user)
):
    query: dict = {"user_id": user_id}
    if unread_only:
        query["read_at"] = None
 
    total = await notifications_collection.count_documents(query)
    unread = await notifications_collection.count_documents({**query, "read_at": None})
 
    cursor = notifications_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
 
    return {
        "user_id": user_id,
        "total": total,
        "unread": unread,
        "notifications": [serialize(doc) for doc in docs]
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /notify/status — list all notifications
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/status")
async def get_all_notifications(
    status: Optional[NotificationStatus] = None,
    notification_type: Optional[NotificationType] = None,
    limit: int = 20,
    skip: int = 0,
    user=Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if notification_type:
        query["notification_type"] = notification_type

    total = await notifications_collection.count_documents(query)
    cursor = notifications_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    return {
        "total": total,
        "notifications": [serialize(doc) for doc in docs]
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /notify/status/{notification_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/status/{notification_id}")
async def get_notification_status(notification_id: str, user=Depends(get_current_user)):
    try:
        doc = await notifications_collection.find_one({"_id": ObjectId(notification_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID")

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return serialize(doc)


# ─────────────────────────────────────────────────────────────────────────────
# GET /notify/task/{task_id}/history
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/task/{task_id}/history")
async def task_notification_history(task_id: str, user=Depends(get_current_user)):
    docs = await notifications_collection.find({"task_id": task_id}).sort("created_at", -1).to_list(length=50)
    return {
        "total": len(docs),
        "notifications": [serialize(d) for d in docs]
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /notify/bulk
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/bulk")
async def bulk_notify(request: BulkNotifyRequest, user=Depends(get_current_user)):
    queued_ids = []

    for task_id, user_id in zip(request.task_ids, request.recipient_user_ids):
        try:
            db_user = await users_collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            continue

        if not db_user or not db_user.get("email"):
            continue

        try:
            task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
        except Exception:
            task = None
        task = task or {"_id": task_id, "title": f"Task {task_id}"}

        subject, html_body = build_email_content(
            request.notification_type, task, resolve_user_name(db_user)   # ✅ handles profile.name
        )

        doc = {
            "task_id": task_id,
            "user_id": user_id,
            "recipient_email": db_user["email"],
            "notification_type": request.notification_type,
            "status": NotificationStatus.PENDING,
            "subject": subject,
            "body": html_body,
            "retry_count": 0,
            "error_message": None,
            "created_at": datetime.utcnow(),
            "sent_at": None
        }

        result = await notifications_collection.insert_one(doc)
        notification_id = str(result.inserted_id)
        send_email_task.delay(notification_id)
        queued_ids.append(notification_id)

    return {
        "message": "Bulk notifications queued",
        "queued_count": len(queued_ids),
        "notification_ids": queued_ids
    }

# ─────────────────────────────────────────────────────────────────────────────
# POST /notify/user/{user_id} — custom direct message to a user
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/user/{user_id}")
async def notify_user(user_id: str, body: NotifyUserRequest, user=Depends(get_current_user)):

    recipient_email = body.recipient_email
    user_name = "User"

    if not recipient_email:
        try:
            db_user = await users_collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        recipient_email = db_user.get("email")
        user_name = resolve_user_name(db_user)   # handles profile.name

        if not recipient_email:
            raise HTTPException(status_code=400, detail="User has no email address on record")

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;padding:20px;border:1px solid #e0e0e0;border-radius:8px">
        <h2 style="color:#4A90D9">{body.subject}</h2>
        <p>Hi <strong>{user_name}</strong>,</p>
        <p>{body.message}</p>
        <p style="color:#888;font-size:12px">— Task Manager System</p>
    </div>
    """

    doc = {
        "task_id": None,
        "user_id": user_id,
        "recipient_email": recipient_email,
        "notification_type": "direct_message",
        "status": NotificationStatus.PENDING,
        "subject": body.subject,
        "body": html_body,
        "retry_count": 0,
        "error_message": None,
        "created_at": datetime.utcnow(),
        "sent_at": None
    }

    result = await notifications_collection.insert_one(doc)
    notification_id = str(result.inserted_id)
    send_email_task.delay(notification_id)

    return {
        "message": "Notification queued successfully",
        "notification_id": notification_id,
        "status": NotificationStatus.PENDING,
        "recipient_email": recipient_email
    }

# ─────────────────────────────────────────────────────────────────────────────
# DELETE /notify/clear  (admin only)
# Wipe all notification records
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/clear")
async def clear_all_notifications(user=Depends(get_current_user)):
 
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
 
    result = await notifications_collection.delete_many({})
 
    return {
        "message": "All notifications cleared",
        "deleted_count": result.deleted_count
    }

# ─────────────────────────────────────────────────────────────────────────────
# DELETE /notify/{notification_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, user=Depends(get_current_user)):
    try:
        result = await notifications_collection.delete_one({"_id": ObjectId(notification_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID")

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return {"message": "Notification deleted successfully"}
