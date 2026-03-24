from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "task_manager")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

messages_collection = db["messages"]
conversations_collection = db["conversations"]

async def create_indexes():
    await messages_collection.create_index("conversation_id")
    await conversations_collection.create_index("sender_id")
    await conversations_collection.create_index("created_at")
    await conversations_collection.create_index("members")
    await conversations_collection.create_index("created_by")