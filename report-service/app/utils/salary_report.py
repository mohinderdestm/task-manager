from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def generate_salary_pdf(user_id:str, salary_data: dict) -> str:

    file_path = f"salary_report_{user_id}.pdf"

    c= canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    # Header
    c.setFillColor(colors.HexColor("#4A90D9"))
    c.rect(0, height - 80, width, 80, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "Salary Report")

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 68, "Task Manager System")

    # Body
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, height - 120, f"Employee ID: {user_id}")

    y = height - 160
    c.setFont("Helvetica", 12)

    for key, value in salary_data.items():

        if y<80:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 12)

            row_color = colors.HexColor("#F555F5") if list(salary_data.keys()).index(key) % 2 == 0 else colors.white
            c.setFillColor(row_color)
            c.rect(45, y - 8, width - 90, 24, fill=True, stroke=False)

            c.setFillColor(colors.HexColor("#555555"))
            c.setFont("Helvetica-Bold", 11)
            c.drawString(55, y + 4, str(key))

            c.setFillColor(colors.black)
            c.setFont("Helvetica", 11)
            c.drawString(width - 55, y + 4, str(value))

            y -= 30
    
    # Footer
    c.setFillColor(colors.HexColor("#888888"))
    c.setFont("Helvetica", 9)
    c.drawString(50, 40, "This is a system generated report. For any queries, contact HR.")
    
    c.save()
    return file_path

