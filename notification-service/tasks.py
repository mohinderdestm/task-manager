from datetime import datetime, timezone
from bson import ObjectId
import pymongo
import os
from dotenv import load_dotenv

from celery_app import celery
from models import NotificationStatus

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()

_mongo_client = pymongo.MongoClient(os.getenv("MONGO_URI"))
_db = _mongo_client[os.getenv("DB_NAME")]
_notifications = _db["notifications"]

SENDGRID_API_KEY    = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@taskmanager.com")


def _send_email_sync(to_email: str, subject: str, content: str):

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
        return False, f"SendGrid returned status: {response.status_code}"

    except Exception as e:
        return False, f"SendGrid error: {str(e)}"


@celery.task(
    name="tasks.send_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def send_email_task(self, notification_id: str):
    # Fetch doc from MongoDB
    try:
        doc = _notifications.find_one({"_id": ObjectId(notification_id)})
    except Exception as e:
        print(f"❌ DB fetch error for {notification_id}: {e}")
        raise self.retry(exc=e)

    if not doc:
        print(f"⚠️  Notification {notification_id} not found in DB, skipping.")
        return {"status": "skipped", "reason": "not found"}

    recipient_email = doc.get("recipient_email")
    subject = doc.get("subject", "Notification")
    html_body = doc.get("body", "")

    if not recipient_email:
        _notifications.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {
                "status": NotificationStatus.FAILED,
                "error_message": "No recipient email in document"
            }}
        )
        return {"status": "failed", "reason": "no recipient email"}

    # Send email via SendGrid (sync)
    success, error_msg = _send_email_sync(recipient_email, subject, html_body)

    # Success
    if success:
        _notifications.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {
                "status": NotificationStatus.SENT,
                "sent_at": datetime.now(timezone.utc),
                "error_message": None
            }}
        )
        print(f"✅  Email sent: {notification_id} → {recipient_email}")
        return {"status": "sent", "notification_id": notification_id}

    # Failure → retry
    retry_count = self.request.retries
    _notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {
            "status": NotificationStatus.FAILED,
            "error_message": error_msg,
            "retry_count": retry_count
        }}
    )
    print(f"❌  Email failed for {notification_id} (attempt {retry_count}): {error_msg}")
    raise self.retry(exc=Exception(error_msg))