from fastapi import FastAPI
from app.router import router
import os

app = FastAPI(
    title="Report Service",
    description="Service responsible for generating reports"
)

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Report Service is running"}


@app.get("/health")
async def health():
    port = int(os.getenv("PORT", 3006))    
    return {"status": "healthy", "service": "report-service", "port": port}