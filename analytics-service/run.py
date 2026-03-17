import uvicorn
import os
from dotenv import load_dotenv

load_dotenv() 

PORT = int(os.getenv("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run("app.main:app",port=PORT, reload=True)