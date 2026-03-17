from fastapi import FastAPI
from .router import router
import os
import uvicorn

app = FastAPI(title="User Service")

PORT = int(os.getenv("PORT", 8001))


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)


app.include_router(router)