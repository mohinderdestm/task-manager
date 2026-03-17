from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx

from app.config import MONGO_URI, DB_NAME, AUTH_SERVICE_URL

# -----------------------------
# Security
# -----------------------------
security = HTTPBearer()

# -----------------------------
# MongoDB Client
# -----------------------------
mongo_client = AsyncIOMotorClient(MONGO_URI)

db = mongo_client[DB_NAME]


async def get_db():
    return db


# -----------------------------
# Auth validation
# -----------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{AUTH_SERVICE_URL}/auth/validate",
                headers={"Authorization": f"Bearer {token}"}
            )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Auth service unavailable"
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    data = resp.json()

    if not data.get("valid"):
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    return {
        "id": data["user_id"],
        "email": data["email"]
    }