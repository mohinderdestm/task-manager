import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

def send_email(receiver_email, file_path):

   
    sender_email = os.getenv("EMAIL_USER")
    password =  os.getenv("EMAIL_PASS")

    msg = EmailMessage()
    msg["Subject"] = "Your Analytics Report"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    msg.set_content("Please find your report attached.")

    # Attach PDF
    with open(file_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=file_path
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, password)
        smtp.send_message(msg)