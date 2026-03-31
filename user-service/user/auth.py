from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
import jwt
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

security = HTTPBearer()

async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        print("DECODED PAYLOAD:", payload)

        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "role": payload.get("role", "employee"),
            "name":payload.get("name")
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

    except jwt.InvalidTokenError as e:
        print("JWT ERROR:", e)
        raise HTTPException(status_code=401, detail="Invalid token")

#  decorator to enforce role-based access
def require_roles(roles: list):
    from fastapi import Depends

    async def role_checker(token_data: dict = Depends(validate_token)):
        user_role = token_data.get("role", "employee")
        if user_role not in roles:
            raise HTTPException(status_code=403, detail="Access denied")
        return token_data

    return role_checker