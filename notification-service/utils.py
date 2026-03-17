import os
import jwt
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from models import NotificationType

load_dotenv()

SECRET_KEY          = os.getenv("JWT_SECRET_KEY")
ALGORITHM           = os.getenv("JWT_ALGORITHM", "HS256")
SENDGRID_API_KEY    = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@taskmanager.com")


# ── JWT ──────────────────────────────────────────────────────────
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None


# ── Email Templates ──────────────────────────────────────────────
def build_email_content(notification_type: NotificationType, task: dict, user_name: str):
    title   = task.get("title", f"Task {task.get('_id', '')}")
    task_id = str(task.get("_id", ""))

    if notification_type == NotificationType.TASK_ASSIGNED:
        subject = f"📋 New Task Assigned: {title}"
        body    = f"Hi {user_name}, you have been assigned a new task: {title} (ID: {task_id})."
    elif notification_type == NotificationType.TASK_COMPLETED:
        subject = f"✅ Task Completed: {title}"
        body    = f"Hi {user_name}, task '{title}' (ID: {task_id}) has been marked as completed."
    elif notification_type == NotificationType.TASK_UPDATED:
        subject = f"✏️ Task Updated: {title}"
        body    = f"Hi {user_name}, task '{title}' (ID: {task_id}) has been updated."
    elif notification_type == NotificationType.TASK_DELETED:
        subject = f"🗑️ Task Deleted: {title}"
        body    = f"Hi {user_name}, task '{title}' (ID: {task_id}) has been deleted."
    elif notification_type == NotificationType.TASK_OVERDUE:
        subject = f"⚠️ Task Overdue: {title}"
        body    = f"Hi {user_name}, task '{title}' (ID: {task_id}) is overdue. Please prioritize it."
    else:
        subject = "Task Notification"
        body    = "You have a new notification regarding your tasks."

    return subject, body


# ── Email Sending ────────────────────────────────────────────────
async def send_email(to_email: str, subject: str, content: str):
    if not SENDGRID_API_KEY:
        print(f"[DEV MODE] Email → {to_email} | Subject: {subject}")
        return True, ""

    try:
        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=content
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in (200, 201, 202):
            return True, "Email sent successfully"
        return False, f"Failed to send email: {response.status_code}"

    except Exception as e:
        return False, f"Failed to send email: {str(e)}"