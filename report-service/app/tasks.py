import asyncio
from app.celery_app import celery_app
from app.report_service import get_user_task_report
from app.utils.pdf_generator import generate_pdf
from app.utils.csv_generator import generate_csv


@celery_app.task
def generate_report_task(user_id: str):
    # Run async function inside sync Celery task
    report = asyncio.run(get_user_task_report(user_id))

    pdf_file = generate_pdf(report)
    csv_file = generate_csv(report)

    return {
        "status": "completed",
        "pdf_file": pdf_file,
        "csv_file": csv_file
    }