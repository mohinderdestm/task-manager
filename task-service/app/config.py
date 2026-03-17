import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

# -----------------------------
# MongoDB
# -----------------------------
MONGO_URI = os.getenv(
    "MONGO_URI"
)

DB_NAME = os.getenv("DB_NAME")

# -----------------------------
# Service URLs
# -----------------------------
AUTH_SERVICE_URL = os.getenv(
    "AUTH_SERVICE_URL",
    "http://127.0.0.1:8001"
)

USER_SERVICE_URL = os.getenv(
    "USER_SERVICE_URL",
    "http://127.0.0.1:8002"
)

NOTIFICATION_URL = os.getenv(
    "NOTIFICATION_URL",
    "http://127.0.0.1:8005"
)

# -----------------------------
# Security
# -----------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "secret")

# -----------------------------
# Service Port
# -----------------------------

SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8003))
