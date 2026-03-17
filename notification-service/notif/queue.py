import asyncio
from datetime import datetime
from bson import ObjectId

from database import notifications_collection
from models import NotificationStatus
from utils import send_email

notification_queue: asyncio.Queue = asyncio.Queue()
MAX_RETRIES = 3


async def process_notifications(notification_id: str):
    try:
        doc = await notifications_collection.find_one({"_id": ObjectId(notification_id)})

        if not doc or doc["status"] != NotificationStatus.PENDING:
            return

        await notifications_collection.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"status": NotificationStatus.QUEUED}}
        )

        success, error_msg = await send_email(
            to_email=doc["recipient_email"],
            subject=doc["subject"],
            content=doc["body"]
        )

        if success:
            await notifications_collection.update_one(
                {"_id": ObjectId(notification_id)},
                {"$set": {
                    "status": NotificationStatus.SENT,
                    "sent_at": datetime.utcnow(),
                    "error_message": None
                }}
            )
            print(f"✅ Sent notification {notification_id} → {doc['recipient_email']}")
        else:
            retry_count = doc.get("retry_count", 0) + 1
            new_status = NotificationStatus.FAILED if retry_count >= MAX_RETRIES else NotificationStatus.PENDING
            await notifications_collection.update_one(
                {"_id": ObjectId(notification_id)},
                {"$set": {
                    "status": new_status,
                    "error_message": error_msg,
                    "retry_count": retry_count
                }}
            )
            if new_status == NotificationStatus.PENDING:
                await asyncio.sleep(2 ** retry_count)
                await notification_queue.put(notification_id)

    except Exception as e:
        print(f"❌ Error processing notification {notification_id}: {e}")
        await notifications_collection.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"status": NotificationStatus.FAILED, "error_message": str(e)}}
        )


async def queue_worker():
    print("🚀 Notification queue worker started")
    while True:
        try:
            notification_id = await notification_queue.get()
            await process_notifications(notification_id)
            notification_queue.task_done()
        except Exception as e:
            print(f"❌ Error in queue worker: {e}")
            await asyncio.sleep(1)