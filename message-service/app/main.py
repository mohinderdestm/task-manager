from fastapi import FastAPI,Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.router import router

app = FastAPI(title="Message Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8005",
        "http://127.0.0.1:8005",
    ],
     allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="app/templates")

app.include_router(router)

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})