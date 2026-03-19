from celery import Celery

celery = Celery(
    "worker",
    broker="redis://localhost:6379/0",   # Redis as broker
    backend="redis://localhost:6379/0",   # Redis as result backend
    include=["app.tasks.analytics_tasks"]
)