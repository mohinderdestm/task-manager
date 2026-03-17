from fastapi import FastAPI
from pydantic import BaseModel
from app.tasks import send_report_email

app = FastAPI()

@app.get("/")
def Home():
    return{"API is running"}

class EmailRequest(BaseModel):
    email: str

@app.post("/send-report")
def send_report(email: str):
    send_report_email.delay(email)
    return {"message": "Report is being sent in background"}


