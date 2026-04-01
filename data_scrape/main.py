from fastapi import FastAPI
from scraper import scrape_books
from db import books_collection

app = FastAPI()

@app.post("/scrape")
async def scrape_and_store():
    books = await scrape_books()

    if books:
        batch_size = 100

        for i in range(0, len(books), batch_size):
            batch = books[i:i + batch_size]
            await books_collection.insert_many(batch)

    return {
        "message": "Data scraped and stored",
        "count": len(books)
    }


@app.get("/book/{slug}")
async def get_book(slug: str):
    slug = slug.strip()  # safety

    book = await books_collection.find_one(
        {"slug": slug},
        {"_id": 0}
    )

    return book


@app.get("/books")
async def get_all_books(limit: int = 10, skip: int = 0):
    books = await books_collection.find(
        {}, {"_id": 0}
    ).skip(skip).limit(limit).to_list(limit)

    return books

@app.get("/books/category/{category}")
async def get_books_by_category(category: str, limit: int = 10, skip: int = 0):
    books = await books_collection.find(
        {"category": category},
        {"_id": 0}
    ).skip(skip).limit(limit).to_list(limit)

    return books

@app.get("/books/rating/{rating}")
async def get_books_by_rating(rating: str):
    books = await books_collection.find(
        {"rating": rating},
        {"_id": 0}
    ).to_list(50)

    return books

@app.get("/categories")
async def get_categories():
    categories = await books_collection.distinct("category")
    return categories