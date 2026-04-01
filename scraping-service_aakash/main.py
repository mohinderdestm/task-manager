from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import connect_db, close_db, get_db
from db_setup import create_collections
from router import router
import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", 3009))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await create_collections(get_db())
    yield
    await close_db()


app = FastAPI(
    title="Book Scraping Service",
    description="A service to scrape data and store it in MongoDB",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api")

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Book-Scraping-Service",
        "status": "running",
        "port": PORT,
        "docs": f"http://localhost:{PORT}/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

