from fastapi import APIRouter
from app.services.analytic_services import AnalyticsService
from app.tasks.analytics_tasks import calculate_user_reports
from celery.result import AsyncResult
from app.celery_app import celery
from app.database.db import task_collection
from bson import ObjectId

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/user/{id}/stats")
async def user_stats(id: str):
    return await AnalyticsService.get_user_stats(id)


@router.get("/dashboard")
async def dashboard_stats(period: str = "week"):
    return await AnalyticsService.get_dashboard_stats(period)

@router.get("/analytics/{user_id}")
async def get_user_analytics(user_id: str):

    user_object_id = ObjectId(user_id)

    tasks = await task_collection.find(
        {"created_by": user_object_id},
        {"_id": 0,
        "created_by": 0}
    ).to_list(length=None)

    user_email = "arshpreetsingh1907@gmail.com" 

    task = calculate_user_reports.delay(tasks,user_email)

    return {
        "message": "Analytics started",
        "task_id": task.id
    }

@router.get("/analytics/result/{task_id}")
async def get_result(task_id: str):

    result = AsyncResult(task_id, app=celery)

    return {
        "status": result.status,
        "result": result.result
    }
