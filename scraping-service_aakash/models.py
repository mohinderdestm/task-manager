from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BookModel(BaseModel):
    title: str
    price: float
    rating: int
    availability: str
    category: str
    description: str
    image_url: str
    product_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScrapeResponse(BaseModel):
    message: str
    total_scraped: int
    total_saved: int
    duplicates_skipped: int


class BookOut(BaseModel):
    title: str
    price: float
    rating: int
    availability: str
    category: str
    description: str
    image_url: str
    product_url: str
    created_at: datetime


class PaginatedBooks(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    books: list[BookOut]


class StatsResponse(BaseModel):
    total_books: int
    total_categories: int
    average_price: float
    min_price: float
    max_price: float
    in_stock: int
    out_of_stock: int
    rating_distribution: dict


