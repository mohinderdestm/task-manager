from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging

from database import create_indexes
from messaging.router import router as messaging_router
from dependencies import get_current_user

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Message Service",
    description="Real-time messaging microservice with WebSockets",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(messaging_router, prefix="/messaging", tags=["Messaging"])

@app.get("/")
async def root():
    return {
        "service": "Message Service",
        "version": "1.0.0",
        "status": "running",
        "port": os.getenv("PORT", 3008),
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status":"healthy"}

@app.get("/chat")
async def chat_ui(request: Request):

    ws_host = os.getenv("WS_HOST", "localhost")
    port = os.getenv("PORT", 3008)
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "ws_url": f"ws://{ws_host}:{port}/messaging/ws",
        "api_url": f"http://{ws_host}:{port}",
    })

app.on_event("startup")
async def startup_event():
    await create_indexes()
    logger.info("Message service started on port %s", os.getenv("PORT", 3008))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 3008)), reload=True)

