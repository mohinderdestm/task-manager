from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from books_scraper import scrape_all
from database import books_collection
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError
from typing import Optional

router = APIRouter()


async def save_books(data):
    for book in data:
        try:
            await books_collection.update_one(
                {"product_url": book["product_url"]},
                {"$set": book},
                upsert=True
            )
        except PyMongoError as e:
            print(f"MongoDB error: {e}")


#  Trigger Scraping
@router.post("/scrape", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scrape(background_tasks: BackgroundTasks, category: str = None, pages: int = None):

    if pages is not None and pages < 1:
        raise HTTPException(status_code=400, detail="Pages must be >= 1")

    async def run():
        try:
            data = await scrape_all(category, pages)
            await save_books(data)
        except Exception as e:
            print("Scraping failed:", e)

    background_tasks.add_task(run)

    return {"message": "Scraping started"}


# Get All Books    
@router.get("/books")
async def get_books(page: int = 1, limit: int = 20):

    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    if limit > 100:
        raise HTTPException(status_code=400, detail="Limit too large")

    skip = (page - 1) * limit

    cursor = books_collection.find().skip(skip).limit(limit)
    data = await cursor.to_list(length=limit)

    total = await books_collection.count_documents({})

    for d in data:
        d["_id"] = str(d["_id"])

    return {"total": total, "page": page, "data": data}


@router.post("/scrape-preview")
async def scrape_preview(category: str = None, pages: int = 1):

    if pages > 3:
        raise HTTPException(status_code=400, detail="Limit pages for preview")

    data = await scrape_all(category, pages)

    return {
        "total": len(data),
        "sample": data[:5]
    }


from typing import Optional
from fastapi import HTTPException

@router.get("/books/search")
async def search_books(
    q: Optional[str] = None,
    rating: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    availability: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    limit: int = 10
):

    if not any([q, category, rating, min_price, max_price, availability]):
        raise HTTPException(
            status_code=400,
            detail="At least one search parameter is required"
        )

    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    skip = (page - 1) * limit

    query = {}

    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}}
        ]

    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    if rating:
        query["rating"] = rating

    if min_price is not None or max_price is not None:
        query["price"] = {}
        if min_price is not None:
            query["price"]["$gte"] = min_price
        if max_price is not None:
            query["price"]["$lte"] = max_price

    if availability:
        query["availability"] = {"$regex": availability, "$options": "i"}

    cursor = books_collection.find(query).skip(skip).limit(limit)
    data = await cursor.to_list(length=limit)

    total = await books_collection.count_documents(query)

    for d in data:
        d["_id"] = str(d["_id"])

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": data
    }


# Get Book by ID
@router.get("/books/{id}")
async def get_book(id: str):

    try:
        obj_id = ObjectId(id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    book = await books_collection.find_one({"_id": obj_id})

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book["_id"] = str(book["_id"])
    return book


# Delete All Books
@router.delete("/books")
async def delete_all():
    result = await books_collection.delete_many({})
    return {"deleted": result.deleted_count}