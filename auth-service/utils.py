import os
from fastapi import HTTPException,status
from datetime import datetime, timedelta
from typing import Union, Any
import jwt
# from jwt import PyJWTError
from dotenv import load_dotenv
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")
EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES"))
EXPIRY_DAYS = int(os.getenv("JWT_EXPIRY_DAYS"))


def hash_password(password: str) -> str:
    password = password.strip()
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    
    if len(password.encode('utf-8')) > 72:
        raise ValueError("Password too long (max 72 characters)")
    
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(payload:dict):
   to_encode = payload.copy()
   issued_at = datetime.utcnow()
   expire = issued_at + timedelta(minutes=EXPIRY_MINUTES)

   to_encode.update({
      "iat":issued_at,
      "exp":expire
      })

   token = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
   return token , issued_at, expire


def create_refresh_token(payload:dict):
   to_encode = payload.copy()

   issued_at = datetime.utcnow()
   expire = issued_at + timedelta(days=EXPIRY_DAYS)

   to_encode.update({
      "iat":issued_at,
      "exp":expire
      })

   token = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
   return token 


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None
    