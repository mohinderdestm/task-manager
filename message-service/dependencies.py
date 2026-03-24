from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY","your_secret_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM","HS256")

security = HTTPBearer()

def verify_token(token:str) -> dict:
    try:
        payload = jwt.decode(token,JWT_SECRET_KEY,algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return verify_token(credentials.credentials)

# For WebSocket connections, we can not use the standard HTTPBearer dependency,
# so create a separate function to extract the token from query parameters.
def get_user_from_token_param(token: str = Query(...)) -> dict:
    return verify_token(token)
