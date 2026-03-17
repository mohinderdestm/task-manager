from fastapi import FastAPI
from app.routers import tasks

app = FastAPI(
    title="Task Service",
    version="1.0"
)

app.include_router(tasks.router)

@app.get("/")
def health():
    return {"service": "Task Service running"}