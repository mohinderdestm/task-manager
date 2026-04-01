from fastapi import FastAPI
from contextlib import asynccontextmanager
from router import router
from database import create_indexes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    
    yield 


app = FastAPI(lifespan=lifespan)

app.include_router(router)