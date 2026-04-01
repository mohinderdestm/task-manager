from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from database import get_db
from models import ScrapeResponse, BookOut, PaginatedBooks, StatsResponse
from scraper import scrape_all_books, scrape_page, scrape_category, get_all_categories
import math

router = APIRouter()


# ─────────────────────────────────────────────
#  SCRAPING ENDPOINTS
# ─────────────────────────────────────────────

@router.post("/scrape/all", response_model=ScrapeResponse, tags=["Scraping"])
async def scrape_all():
    db = get_db()
    books = scrape_all_books(delay=0.2)

    if not books:
        raise HTTPException(status_code=500, detail="Scraping failed — no books returned")

    saved = 0
    skipped = 0
    for book in books:
        book["created_at"] = datetime.utcnow()
        # Upsert: avoid duplicates by product_url
        result = await db["books"].update_one(
            {"product_url": book["product_url"]},
            {"$set": book},
            upsert=True
        )
        if result.upserted_id:
            saved += 1
        else:
            skipped += 1

    return ScrapeResponse(
        message="Full scrape completed successfully",
        total_scraped=len(books),
        total_saved=saved,
        duplicates_skipped=skipped,
    )


@router.post("/scrape/page/{page_number}", response_model=ScrapeResponse, tags=["Scraping"])
async def scrape_single_page(page_number: int):
    if page_number < 1 or page_number > 50:
        raise HTTPException(status_code=400, detail="Page number must be between 1 and 50")

    db = get_db()
    books = scrape_page(page_number)

    if not books:
        raise HTTPException(status_code=500, detail=f"Failed to scrape page {page_number}")

    saved = 0
    skipped = 0
    for book in books:
        book["created_at"] = datetime.utcnow()
        result = await db["books"].update_one(
            {"product_url": book["product_url"]},
            {"$set": book},
            upsert=True
        )
        if result.upserted_id:
            saved += 1
        else:
            skipped += 1

    return ScrapeResponse(
        message=f"Page {page_number} scraped successfully",
        total_scraped=len(books),
        total_saved=saved,
        duplicates_skipped=skipped,
    )


@router.post("/scrape/category/{category_name}", response_model=ScrapeResponse, tags=["Scraping"])
async def scrape_by_category(category_name: str):
    db = get_db()
    books = scrape_category(category_name, delay=0.2)

    if not books:
        raise HTTPException(
            status_code=404,
            detail=f"No books found for category '{category_name}'. Check GET /categories for valid names."
        )

    saved = 0
    skipped = 0
    for book in books:
        book["created_at"] = datetime.utcnow()
        result = await db["books"].update_one(
            {"product_url": book["product_url"]},
            {"$set": book},
            upsert=True
        )
        if result.upserted_id:
            saved += 1
        else:
            skipped += 1

    return ScrapeResponse(
        message=f"Category '{category_name}' scraped successfully",
        total_scraped=len(books),
        total_saved=saved,
        duplicates_skipped=skipped,
    )


# ─────────────────────────────────────────────
#  READ ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/books", response_model=PaginatedBooks, tags=["Books"])
async def get_all_books(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Books per page"),
):
    db = get_db()
    skip = (page - 1) * page_size
    total = await db["books"].count_documents({})
    cursor = db["books"].find({}, {"_id": 0}).skip(skip).limit(page_size)
    books = await cursor.to_list(length=page_size)

    return PaginatedBooks(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
        books=books,
    )


@router.get("/books/search", response_model=list[BookOut], tags=["Books"])
async def search_books(
    q: str = Query(..., description="Search keyword in book title"),
    limit: int = Query(10, ge=1, le=50),
):
    db = get_db()
    cursor = db["books"].find(
        {"title": {"$regex": q, "$options": "i"}},
        {"_id": 0}
    ).limit(limit)
    books = await cursor.to_list(length=limit)

    if not books:
        raise HTTPException(status_code=404, detail=f"No books found matching '{q}'")
    return books


@router.get("/books/category/{category_name}", response_model=PaginatedBooks, tags=["Books"])
async def get_books_by_category(
    category_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    db = get_db()
    query = {"category": {"$regex": category_name, "$options": "i"}}
    skip = (page - 1) * page_size
    total = await db["books"].count_documents(query)

    if total == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No books found for category '{category_name}'. Scrape it first via POST /scrape/category/{category_name}"
        )

    cursor = db["books"].find(query, {"_id": 0}).skip(skip).limit(page_size)
    books = await cursor.to_list(length=page_size)

    return PaginatedBooks(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
        books=books,
    )


@router.get("/books/rating/{stars}", response_model=list[BookOut], tags=["Books"])
async def get_books_by_rating(
    stars: int,
    limit: int = Query(20, ge=1, le=100),
):
    if stars < 1 or stars > 5:
        raise HTTPException(status_code=400, detail="Stars must be between 1 and 5")

    db = get_db()
    cursor = db["books"].find({"rating": stars}, {"_id": 0}).limit(limit)
    books = await cursor.to_list(length=limit)

    if not books:
        raise HTTPException(status_code=404, detail=f"No books found with {stars}-star rating")
    return books


@router.get("/books/price-range", response_model=list[BookOut], tags=["Books"])
async def get_books_by_price_range(
    min_price: float = Query(0.0, description="Minimum price in £"),
    max_price: float = Query(100.0, description="Maximum price in £"),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_db()
    query = {"price": {"$gte": min_price, "$lte": max_price}}
    cursor = db["books"].find(query, {"_id": 0}).sort("price", 1).limit(limit)
    books = await cursor.to_list(length=limit)

    if not books:
        raise HTTPException(
            status_code=404,
            detail=f"No books found between £{min_price} and £{max_price}"
        )
    return books


@router.get("/categories", tags=["Books"])
async def list_all_categories():
    categories = get_all_categories()
    if not categories:
        raise HTTPException(status_code=500, detail="Could not fetch categories")
    return {"total": len(categories), "categories": [c["name"] for c in categories]}


@router.get("/categories/stored", tags=["Books"])
async def list_stored_categories():
    db = get_db()
    categories = await db["books"].distinct("category")
    return {"total": len(categories), "categories": sorted(categories)}


# ─────────────────────────────────────────────
#  STATS ENDPOINT
# ─────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse, tags=["Stats"])
async def get_stats():
    db = get_db()
    total = await db["books"].count_documents({})
    if total == 0:
        raise HTTPException(status_code=404, detail="No books in database. Scrape first!")

    pipeline = [
        {
            "$group": {
                "_id": None,
                "avg_price": {"$avg": "$price"},
                "min_price": {"$min": "$price"},
                "max_price": {"$max": "$price"},
            }
        }
    ]
    price_stats = await db["books"].aggregate(pipeline).to_list(1)
    price_data = price_stats[0] if price_stats else {}

    # Rating distribution
    rating_pipeline = [
        {"$group": {"_id": "$rating", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    rating_data = await db["books"].aggregate(rating_pipeline).to_list(10)
    rating_dist = {item["_id"]: item["count"] for item in rating_data}

    # Stock counts
    in_stock = await db["books"].count_documents({"availability": {"$regex": "In stock", "$options": "i"}})
    out_of_stock = await db["books"].count_documents({"availability": {"$regex": "Out of stock", "$options": "i"}})

    # Category count
    categories = await db["books"].distinct("category")

    return StatsResponse(
        total_books=total,
        total_categories=len(categories),
        average_price=round(price_data.get("avg_price", 0), 2),
        min_price=price_data.get("min_price", 0),
        max_price=price_data.get("max_price", 0),
        in_stock=in_stock,
        out_of_stock=out_of_stock,
        rating_distribution=rating_dist,
    )


# ─────────────────────────────────────────────
#  DELETE ENDPOINTS
# ─────────────────────────────────────────────

@router.delete("/books/clear", tags=["Admin"])
async def clear_all_books():
    db = get_db()
    result = await db["books"].delete_many({})
    return {"message": f"Cleared {result.deleted_count} books from database"}


@router.delete("/books/category/{category_name}", tags=["Admin"])
async def clear_books_by_category(category_name: str):
    db = get_db()
    result = await db["books"].delete_many(
        {"category": {"$regex": category_name, "$options": "i"}}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No books found for category '{category_name}'")
    return {"message": f"Deleted {result.deleted_count} books from category '{category_name}'"}