import asyncio
import base64
import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.report_service import get_user_task_report
from app.utils.csv_generator import generate_csv
from app.utils.pdf_generator import generate_pdf
from app.utils.salary_report import generate_salary_pdf

router = APIRouter(prefix="/reports", tags=["Reports"])

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://127.0.0.1:3004")

# GET /reports/user/{user_id}
# returns task report in json, pdf, or csv format
@router.get("/user/{user_id}")
async def user_report(user_id: str, report_format: str = "json"):

    report = await get_user_task_report(user_id)

    if report_format == "pdf":
        file = generate_pdf(report, user_id)
        return FileResponse(file, media_type="application/pdf",
                            filename=f"report_{user_id}.pdf")

    if report_format == "csv":
        file = generate_csv(report, user_id)
        return FileResponse(file, media_type="text/csv",
                            filename=f"report_{user_id}.csv")

    return report

# POST /reports/generate
# Generates both PDF and CSV for a user and returns file paths
@router.post("/generate")
async def generate_report(user_id: str):

    report = await get_user_task_report(user_id)

    pdf_file = generate_pdf(report, user_id)
    csv_file = generate_csv(report, user_id)

    return {
        "message": "Report generated",
        "pdf_file": pdf_file,
        "csv_file": csv_file
    }

# GET /reports/download/{file_name}
# Download a generated report file by name
@router.get("/reports/download/{file_name}")
async def download_report(file_name: str):
    file_path = f"./{file_name}"

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/octet-stream"
    )

# POST /reports/salary/{user_id}/send
# Generates a salary report PDF and sends it to the user via email
@router.post("/salary/{user_id}/send")
async def send_salary_report(user_id: str, recipient_email: str):

    salary_data = {
        "Employee ID": user_id,
        "Month": "March 2026",
        "Base Salary": "₹50,000",
        "Bonuses": "₹5,000",
        "Deductions": "₹3,000",
        "Net Salary": "₹52,000"
    }
    pdf_path = generate_salary_pdf(user_id, salary_data)

    try:
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read generated PDF: {str(e)}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notify/email-with-attachment",
                json={
                    "recipient_email": recipient_email,
                    "subject": f"Your Salary Report — March 2026",
                    "message": f"Hi, please find your salary report for March 2026 attached.",
                    "attachment_base64": pdf_base64,
                    "attachment_filename": f"salary_report_{user_id}.pdf",
                    "attachment_type": "application/pdf"
                },
                timeout=10.0
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Notification service is unavailable. Please try again later."
            )
    
    if response.status_code not in (200, 202):
        raise HTTPException(
            status_code=502,
            detail=f"Notification service returned error: {response.status_code}"
        )
    
    return {
        "message": "Salary report generated and queued for delivery",
        "recipient_email": recipient_email,
        "notification_id": response.json().get("notification_id"),
        "pdf_file": pdf_path
    }