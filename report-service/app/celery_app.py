from celery import Celery

celery_app = Celery(
    "report_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.tasks"]   
)

# celery_app.conf.task_routes = {
#     "app.tasks.*": {"queue": "reports"}
# }

# celery -A app.celery_app.celery_app worker --pool=solo --loglevel=info
 