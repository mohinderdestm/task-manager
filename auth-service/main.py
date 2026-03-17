import os
import uvicorn
from fastapi import FastAPI , HTTPException,Request
from utils import create_access_token 
from database import collection 
from models import User,RefreshRequest,UserLogin
from utils import create_access_token, verify_token, hash_password, create_refresh_token , verify_password
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

# test branch
app = FastAPI()

PORT = int(os.getenv("PORT", 8000))

security = HTTPBearer()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)

@app.get("/")
async def main():
    return "hello"

@app.post("/auth/signup")
async def signup(user:User):
      
    existing_user = await collection.find_one({"email":user.email})

    if existing_user:
        raise HTTPException(status_code=400,detail="user already exists")

    
      
    user_data = user.model_dump()
    user_data["password"] = hash_password(user_data["password"])
    user_data["role"] = user_data.get("role", "employee")
    
    result = await collection.insert_one(user_data)
    
    token, issued_at ,expire = create_access_token({
            "user_id":str(result.inserted_id),
            "email":user.email,
            "role": user_data["role"] 
        })

    refresh_token = create_refresh_token({
            "user_id":str(result.inserted_id),
            "email":user.email
        })
    
    await collection.update_one(
    {"email": user.email},
    {"$set": {"refresh_token": refresh_token}} 
    )
      
    return {
        "message":"Signup Sucessfull",
        "access_token": token,
        "refresh_token":refresh_token,
        "issued_at": issued_at,
        "token_type":"bearer",
        "expires_at":expire,
        }


@app.post("/auth/login")
async def sign_in(user: UserLogin):

    db_user = await collection.find_one({
        "email": user.email
    })

    if not db_user:
        return {"message": "User not found"}

    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")

    db_user["_id"] = str(db_user["_id"])

    token = create_access_token({
        "user_id": db_user["_id"],
        "email": db_user["email"],
        "role": db_user.get("role", "employee") 
    })
    
    return {
        "user": {
            "id": db_user["_id"],
            "email": db_user["email"],
            "role": db_user.get("role", "employee")
        },
        "access_token": token,
        
    }

@app.get("/auth/validate")
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials  
    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "valid": True,
        "user_id": payload.get("user_id"),
        "email": payload.get("email"),
         "role": payload.get("role")
    }

@app.post("/auth/refresh")
async def refresh_token(request:RefreshRequest):
    payload = verify_token(request.refresh_token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    new_token, issued_at, expire = create_access_token({
        "user_id": payload.get("user_id"),
        "email": payload.get("email"),
        "role": payload.get("role")  
    })

    return {
        "access_token": new_token,
        "issued_at": issued_at,
        "expires_at": expire
    }

@app.post("/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):

    token = credentials.credentials  
    payload = verify_token(token)

    await collection.update_one(
        {"email": payload.get("email")},
        {"$unset": {"refresh_token": ""}} 
    )

    return {
        "message":"User Logout Successfully"
    }