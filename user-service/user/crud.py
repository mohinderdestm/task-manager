from user.database import users_collection
from bson import ObjectId
from bson.errors import InvalidId


async def get_user(user_id: str):

    print("Searching user:", user_id)

    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except InvalidId:
        return None

    if user:
        user["id"] = str(user["_id"])
        user.pop("_id", None)

        
        user.pop("password", None)
        user.pop("refresh_token", None)

       
        if "profile" not in user:
            user["profile"] = {
                "name": user.get("name"),
                "avatar": user.get("avatar", None),
                "bio": user.get("bio", None),
                "department": user.get("department", None)
            }

        user.pop("name", None)

    return user


async def update_user(user_id: str, data: dict):

    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": data}
    )

    return await get_user(user_id)


async def get_all_users():

    users = []

    async for user in users_collection.find():
        user["id"] = str(user["_id"])
        user.pop("_id")

        user.pop("password", None)
        user.pop("refresh_token", None)
        
        if "profile" not in user:
            user["profile"] = {
                "name": user.get("name"),
                "avatar": user.get("avatar", None),
                "bio": user.get("bio", None),
                "department": user.get("department", None)
            }

        users.append(user)

    return users