# 📚 Scraping Service

A FastAPI microservice that scrapes [books.toscrape.com](http://books.toscrape.com) and stores book data in MongoDB Atlas.

**Port:** `3009`

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| FastAPI | Web framework |
| Motor | Async MongoDB driver |
| BeautifulSoup4 + lxml | HTML parsing |
| Requests | HTTP page fetching |
| Pydantic | Data validation |
| MongoDB Atlas | Database |

---

## Project Structure

```
scraping-service/
├── main.py           → App entry point, lifespan (startup/shutdown)
├── database.py       → MongoDB Motor connection
├── db_setup.py       → Creates 'books' collection + indexes on startup
├── models.py         → Pydantic models (BookModel, BookOut, etc.)
├── scraper.py        → Scraping logic (BeautifulSoup)
├── router.py         → All API endpoints
├── requirements.txt  → Dependencies
└── .env              → Environment variables
```

---

## Setup & Installation

```powershell
cd scraping-service
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the root of the service:

```env
MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
DB_NAME=task-manager
PORT=3009
```

Run the server:

```powershell
uvicorn main:app --reload --port 3009
```

Swagger docs available at: `http://localhost:3009/docs`

---

## MongoDB Collection

**Collection name:** `books`  
**Database:** `task-manager`

Each document has the following fields:

| Field | Type | Example |
|-------|------|---------|
| `title` | string | `"A Paris Apartment"` |
| `price` | float | `39.01` |
| `rating` | int (1–5) | `4` |
| `availability` | string | `"In stock (12 available)"` |
| `category` | string | `"Historical Fiction"` |
| `description` | string | `"Bienvenue à Paris! When April..."` |
| `image_url` | string | `"http://books.toscrape.com/media/..."` |
| `product_url` | string | `"http://books.toscrape.com/catalogue/..."` |
| `created_at` | datetime | `2026-04-01T13:43:24.634+00:00` |

**Indexes created at startup:**

| Index Name | Field | Type |
|------------|-------|------|
| `idx_product_url_unique` | `product_url` | Unique |
| `idx_title_text` | `title` | Text search |
| `idx_category` | `category` | Ascending |
| `idx_rating` | `rating` | Ascending |
| `idx_price` | `price` | Ascending |
| `idx_created_at` | `created_at` | Descending |

---

## API Endpoints

### 🔍 Scraping

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/scrape/all` | Scrape all 1000 books (50 pages) and save to MongoDB |
| `POST` | `/api/scrape/page/{page_number}` | Scrape a single page (1–50), 20 books per page |
| `POST` | `/api/scrape/category/{category_name}` | Scrape all books from a specific category |

> **Note:** `POST /api/scrape/all` visits each book's detail page to fetch the description and real category. It makes ~1050 requests total and takes 3–5 minutes.

---

### 📖 Books

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/books` | Get all books with pagination |
| `GET` | `/api/books/search?q={keyword}` | Search books by title keyword |
| `GET` | `/api/books/category/{category_name}` | Get books by category |
| `GET` | `/api/books/rating/{stars}` | Get books by star rating (1–5) |
| `GET` | `/api/books/price-range?min_price=&max_price=` | Get books within a price range (£) |

**Pagination query params** (for `/api/books` and `/api/books/category`):

| Param | Default | Description |
|-------|---------|-------------|
| `page` | `1` | Page number |
| `page_size` | `20` | Results per page (max 100) |

---

### 🏷️ Categories

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/categories` | List all 50 categories from the live website |
| `GET` | `/api/categories/stored` | List only categories already saved in MongoDB |

---

### 📊 Stats

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/stats` | Returns total books, avg/min/max price, rating distribution, stock counts |

**Sample response:**
```json
{
  "total_books": 1000,
  "total_categories": 50,
  "average_price": 35.07,
  "min_price": 10.0,
  "max_price": 59.99,
  "in_stock": 980,
  "out_of_stock": 20,
  "rating_distribution": {
    "1": 200,
    "2": 198,
    "3": 205,
    "4": 197,
    "5": 200
  }
}
```

---

### 🗑️ Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| `DELETE` | `/api/books/clear` | Delete all books from MongoDB |
| `DELETE` | `/api/books/category/{category_name}` | Delete all books of a specific category |

---

## How Scraping Works

```
POST /api/scrape/all
        ↓
Fetch listing page (20 books shown per page)
        ↓
For each book → visit detail page
        ├── Extract description
        └── Extract category (from breadcrumb: Home > Books > [Category] > Title)
        ↓
Upsert into MongoDB (no duplicates — keyed on product_url)
        ↓
Return { total_scraped, total_saved, duplicates_skipped }
```

---

## Quick Start Guide

1. Scrape a single page to test (fast):
```
POST /api/scrape/page/1
```

2. Scrape all 1000 books (takes 3–5 mins):
```
POST /api/scrape/all
```

3. Browse books:
```
GET /api/books?page=1&page_size=20
```

4. Search by title:
```
GET /api/books/search?q=sapiens
```

5. Filter by category:
```
GET /api/books/category/Mystery
```

6. View stats:
```
GET /api/stats
```