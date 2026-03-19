from app.celery_app import celery
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from app.utils.email_utils import send_email


@celery.task
def calculate_user_reports(tasks,user_email):
     
    if not tasks:
            return {"message": "No tasks found"}

    df = pd.DataFrame(tasks)

    status_counts = df["status"].value_counts().to_dict()

    df = df[df["completed_at"].notna()]
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["completed_at"] = pd.to_datetime(df["completed_at"])

    df["duration"] = (df["completed_at"] - df["created_at"]).dt.total_seconds()

    avg_time = df["duration"].mean()

    # ✅ Create PDF
    file_path = f"reports/report_{user_email}.pdf"
    doc = SimpleDocTemplate(file_path)

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("User Analytics Report", styles["Title"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"Status Counts: {status_counts}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"Average Completion Time: {avg_time}", styles["Normal"]))

    doc.build(elements)

    send_email(user_email, file_path)

    return {
        "message": "PDF generated",
        "file": file_path
    }