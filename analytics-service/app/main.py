from fastapi import FastAPI
from app.routes.analytics_routes import router as analytics_router

app = FastAPI(title="Analytics Service")

app.include_router(analytics_router)