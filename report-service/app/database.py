from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

client = AsyncIOMotorClient(MONGO_URL)

db = client["task-manager"]

users_collection = db["users"]
tasks_collection = db["tasks"]
notifications_collection = db["notifications"]