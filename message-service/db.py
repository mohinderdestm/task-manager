from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")

client = AsyncIOMotorClient (MONGO_URL)
db = client[DB_NAME]

user_collection = db["users"]
message_collection = db["arsh-messages"]
conversation_collection = db["arsh-conversations"]
