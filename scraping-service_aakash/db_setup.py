from motor.motor_asyncio import AsyncIOMotorClient
import pymongo


async def create_collections(db: AsyncIOMotorClient):
    # Create 'books' collection with an index on 'title'
    existing = await db.list_collection_names()
    if "books" not in existing:
        await db.create_collection("books")
        print("Created 'books' collection")
    else:
        print("'books' collection already exists")
    
    books = db["books"]

    await books.create_index(
        [("product_url", pymongo.ASCENDING)],
        unique=True,
        name ="idx_product_url_unique"
    )

    await books.create_index(
        [("title", pymongo.TEXT)],
        name="idx_title_text"
    )

    await books.create_index(
        [("category", pymongo.ASCENDING)],
        name="idx_category"
    )

    await books.create_index(
        [("rating", pymongo.ASCENDING)],
        name="idx_rating"
    )

    await books.create_index(
        [("price", pymongo.ASCENDING)],
        name="idx_price"
    )

    await books.create_index(
        [("created_at", pymongo.DESCENDING)],
        name="idx_created_at"
    )

    print("All indexes created on 'books' collection")