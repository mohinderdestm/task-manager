from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_pdf(report: dict, user_id: str = "unknown") -> str:
    
    file_path = f"report_{user_id}.pdf"
    width, height = letter

    c = canvas.Canvas(file_path, pagesize=letter)

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 50, "User Task Report")

    y = height - 100

    for key, value in report.items():

        # New page if running out of space 
        if y < 80:
            c.showPage()
            y = height - 60

        if isinstance(value, dict):
            # Section header for nested dict
            c.setFont("Helvetica-Bold", 12)
            c.drawString(100, y, f"{key}:")
            y -= 22

            c.setFont("Helvetica", 11)
            for sub_key, sub_value in value.items():
                if y < 80:
                    c.showPage()
                    y = height - 60
                    c.setFont("Helvetica", 11)
                c.drawString(120, y, f"{sub_key}: {sub_value}")
                y -= 20
            y -= 10    

        elif isinstance(value, list):
            c.setFont("Helvetica-Bold", 12)
            c.drawString(100, y, f"{key}:")
            y -= 20
            c.setFont("Helvetica", 11)
            for item in value:
                if y < 80:
                    c.showPage()
                    y = height - 60
                    c.setFont("Helvetica", 11)
                c.drawString(120, y, f"• {item}")
                y -= 20
            y -= 10

        else:
            c.setFont("Helvetica", 12)
            c.drawString(100, y, f"{key}: {value}")
            y -= 28

    c.save()
    return file_path