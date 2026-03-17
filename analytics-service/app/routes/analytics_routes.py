from fastapi import APIRouter
from app.services.analytic_services import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/user/{id}/stats")
async def user_stats(id: str):
    return await AnalyticsService.get_user_stats(id)


@router.get("/dashboard")
async def dashboard_stats(period: str = "week"):
    return await AnalyticsService.get_dashboard_stats(period)

@router.get("/user/user-analytics")
async def user_analytics():
    return await AnalyticsService.user_analytics()
