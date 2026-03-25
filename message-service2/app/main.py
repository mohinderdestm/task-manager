from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from app import auth, chat, message, websocket

# import auth
# import chat
# import message
# import websocket

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(message.router)
app.include_router(websocket.router)

@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/home")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/chat/{conversation_id}")
async def chat_page(request: Request, conversation_id: str):
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "conversation_id": conversation_id}
    )