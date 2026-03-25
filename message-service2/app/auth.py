from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.db import user_collection
from app.jwt_auth import create_token

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.post("/signup")
async def signup(data: dict):
    user = await user_collection.find_one({"email": data["email"]})
    if user:
        return {"error": "User already exists"}

    await user_collection.insert_one({
        "name": data["name"],
        "email": data["email"],
        "password": data["password"]
    })

    return {"message": "User created"}

@router.post("/login")
async def login(data: dict):
    user = await user_collection.find_one({"email": data["email"]})

    if not user or user["password"] != data["password"]:
        return {"error": "Invalid credentials"}

    token = create_token(user)

    return {"token": token}