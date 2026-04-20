from app.celery_worker import celery_app
from app.utils.pdf_generator import generate_pdf
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
from dotenv import load_dotenv
import time

load_dotenv()


@celery_app.task
def test_task():
    print("Task started...")
    time.sleep(5)
    print("Task completed!")
    return "Working"


@celery_app.task
def send_report_email(email: str):
    sender_email = os.getenv("EMAIL_USER")
    app_password = os.getenv("EMAIL_PASS")

    # Dummy report data 
    report_data = {
        "Name": "John",
        "Tasks Completed": 12,
        "Pending Tasks": 3,
        "Performance": "Good"
    }

    # Generate PDF
    file_path = "report.pdf"
    generate_pdf(report_data, file_path)

    # Create email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = email
    msg["Subject"] = "Your Report"

    msg.attach(MIMEText("Please find attached your report.", "plain"))

    # Attach PDF
    with open(file_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())

    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={file_path}")
    msg.attach(part)

    # Send email
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, app_password)

    server.send_message(msg)
    server.quit()

    return f"Report sent to {email}"
