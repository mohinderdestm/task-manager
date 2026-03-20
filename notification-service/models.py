from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum


class NotificationType(str, Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_OVERDUE = "task_overdue"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


# ── Webhook from task-service ──────────
class TaskCreatedWebhook(BaseModel):
    task_id: str
    assigned_to: str   # user_id of the assignee
    title: str

class TaskUpdatedWebhook(BaseModel):
    task_id: str
    assigned_to: str        
    title: str
    status: Optional[str] = None  


# ── Manual trigger endpoints ───────────────────────────────────────
class NotifyTaskRequest(BaseModel):
    notification_type: NotificationType = NotificationType.TASK_ASSIGNED
    recipient_email: Optional[EmailStr] = None
    recipient_user_id: Optional[str] = None


class BulkNotifyRequest(BaseModel):
    task_ids: list[str]
    notification_type: NotificationType = NotificationType.TASK_ASSIGNED
    recipient_user_ids: list[str]


class NotifyUserRequest(BaseModel):
    subject: str
    message: str
    recipient_email: Optional[EmailStr] = None

# Email with attachment (used by report-service for salary reports)
class EmailWithAttachmentRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    message: str
    attachment_base64: str          # PDF file encoded as base64 string
    attachment_filename: str        # e.g. "salary_report_abc123.pdf"
    attachment_type: str = "application/pdf"