from fastapi import FastAPI
from app.router import router

app = FastAPI(
    title="Report Service",
    description="Service responsible for generating reports"
)

app.include_router(router)
