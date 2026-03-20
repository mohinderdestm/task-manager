from notif.celery import celery_app
from database import notifications_collection_sync
from notif.utils import send_email
from bson import ObjectId
from datetime import datetime
from models import NotificationStatus



@celery_app.task(bind=True, max_retries=3)
def process_notification(self, notification_id: str):
    try:

        print("Processing:", notification_id)

        doc = notifications_collection_sync.find_one({"_id": ObjectId(notification_id)})

        if not doc or doc["status"] != NotificationStatus.PENDING:
            return

        notifications_collection_sync.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"status": NotificationStatus.QUEUED}}
        )

        print("Processing:", notification_id)
        print("To:", doc["recipient_email"])
        print("Current status:", doc["status"])

    
        success, error_msg = send_email(
            to_email=doc["recipient_email"],
            subject=doc["subject"],
            content=doc["body"]
        )

        if success:
            notifications_collection_sync.update_one(
                {"_id": ObjectId(notification_id)},
                {"$set": {
                    "status": NotificationStatus.SENT,
                    "sent_at": datetime.utcnow(),
                    "error_message": None
                }}
            )
            print("Email sent")
            print(f"Sent notification {notification_id}")
            print("TYPE:", type(send_email))

        else:
            raise Exception(error_msg)

    except Exception as e:
        retry_count = self.request.retries + 1

        if retry_count >= 3:
            notifications_collection_sync.update_one(
                {"_id": ObjectId(notification_id)},
                {"$set": {
                    "status": NotificationStatus.FAILED,
                    "error_message": str(e)
                }}
            )
        else:
            raise self.retry(exc=e, countdown=2 ** retry_count)



