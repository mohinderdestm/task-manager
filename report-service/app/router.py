from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.report_service import get_user_task_report
from app.utils.csv_generator import generate_csv
from app.utils.pdf_generator import generate_pdf
from app.tasks import generate_report_task

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/user/{user_id}")
async def user_report(user_id: str, format: str = "json"):

    report = await get_user_task_report(user_id)

    if format == "pdf":
        file = generate_pdf(report)
        return FileResponse(file, media_type="application/pdf")

    if format == "csv":
        file = generate_csv(report)
        return FileResponse(file, media_type="text/csv")

    return report


# @router.post("/generate")
# async def generate_report(user_id: str):

#     report = await get_user_task_report(user_id)

#     pdf_file = generate_pdf(report)
#     csv_file = generate_csv(report)

#     return {
#         "message": "Report generated",
#         "pdf_file": pdf_file,
#         "csv_file": csv_file
#     }

@router.post("/generate")
async def generate_report(user_id: str):

    task = generate_report_task.delay(user_id)

    return {
        "message": "Report generation started",
        "task_id": task.id,
    }


@router.get("/reports/download/{file_name}")
async def download_report(file_name: str):
    file_path = f"./{file_name}"

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/octet-stream"
    )


from app.celery_app import celery_app


@router.get("/status/{task_id}")
async def get_status(task_id: str):

    task = celery_app.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None
    }