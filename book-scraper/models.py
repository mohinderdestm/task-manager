from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Book(BaseModel):
    title: str
    price: float
    rating: int
    availability: str
    category: str
    product_url: str
    image_url: str
    description: Optional[str] = None
    review_count: Optional[int] = 0
    created_at: datetime = datetime.utcnow()