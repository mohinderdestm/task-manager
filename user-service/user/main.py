from fastapi import FastAPI
from .router import router
import os
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="User Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3009",
        "http://localhost:3009",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
  
PORT = int(os.getenv("PORT", 8001))


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)


app.include_router(router)