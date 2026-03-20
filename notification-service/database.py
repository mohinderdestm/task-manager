# from motor.motor_asyncio import AsyncIOMotorClient
# from dotenv import load_dotenv
# import os

# load_dotenv()

# MONGO_URI = os.getenv("MONGO_URI")
# DB_NAME = os.getenv("DB_NAME")

# client = AsyncIOMotorClient(MONGO_URI)
# db = client[DB_NAME]

# notifications_collection = db["notifications"]
# users_collection = db["users"]
# tasks_collection = db["tasks"]

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

# ✅ Async (FastAPI)
async_client = AsyncIOMotorClient(MONGO_URI)
async_db = async_client[DB_NAME]

notifications_collection = async_db["notifications"]
users_collection = async_db["users"]
tasks_collection = async_db["tasks"]

# ✅ Sync (Celery)
sync_client = MongoClient(MONGO_URI)
sync_db = sync_client[DB_NAME]

notifications_collection_sync = sync_db["notifications"]

