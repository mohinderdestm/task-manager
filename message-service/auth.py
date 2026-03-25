import jwt
from datetime import datetime, timedelta

SECRET = "MYSECRET"

def create_token(user: str):
    payload = {
        "user_id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except:
        return None