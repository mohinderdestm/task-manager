import asyncio
import os
import httpx


ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://127.0.0.1:3002")


async def get_user_task_report(user_id: str):

    async with httpx.AsyncClient() as client:

        user_response, dashboard_response = await asyncio.gather(
            client.get(f"{ANALYTICS_SERVICE_URL}/analytics/user/{user_id}/stats"),
            client.get(f"{ANALYTICS_SERVICE_URL}/analytics/dashboard?period=week")
        )

    if user_response.status_code != 200:
        return {"error": f"Analytics service failed for user stats: {user_response.status_code}"}
 
    if dashboard_response.status_code != 200:
        return {"error": f"Analytics service failed for dashboard: {dashboard_response.status_code}"}

    user_data = user_response.json()
    dashboard_data = dashboard_response.json()

    report = {
        "user_stats": {
            "pending": user_data.get("pending_tasks", 0),
            "in_progress": user_data.get("In_progress_tasks", 0),
            "completed": user_data.get("completed_tasks", 0),
            "cancelled": user_data.get("cancelled_task", 0)
        },
        "weekly_stats": {
            "total_tasks": dashboard_data.get("total_tasks", 0),
            "completed_tasks": dashboard_data.get("completed_tasks", 0)
        },
        "priority_distribution": dashboard_data.get("priority_status", [])
    }

    return report




