from celery import Celery
from dotenv import load_dotenv
load_dotenv()

celery_app = Celery(
    "notif",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery_app.autodiscover_tasks(["notif"])

from notif import queue

# import notif.queue
