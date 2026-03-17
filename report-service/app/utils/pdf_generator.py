from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_pdf(report):

    file_path = "user_report.pdf"

    c = canvas.Canvas(file_path, pagesize=letter)

    c.setFont("Helvetica", 16)
    c.drawString(200, 750, "User Task Report")

    y = 700

    for key, value in report.items():
        text = f"{key} : {value}"
        c.drawString(100, y, text)
        y -= 30

    c.save()

    return file_path