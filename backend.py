import os
import requests
import asyncpg
from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_DSN= os.getenv("POSTGRES_DSN")


app = FastAPI()

# Разрешаем фронту (Vercel) обращаться к API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mini-app-mauve-alpha.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.create_pool(POSTGRES_DSN)
    print("✅ Database connected")

@app.get("/api/files")
async def get_files(request: Request):
    async with app.state.db.acquire() as conn:
        rows = await conn.fetch("SELECT id, file_name, file_id FROM materials ORDER BY created_at DESC LIMIT 50")
    
    files = []
    for row in rows:
        file_id = row["file_id"]
        name = row["file_name"] or "Без названия"
        
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}")
            data = r.json()
            if "result" not in data:
                continue
            file_path = data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            files.append({"name": name, "url": download_url})
        except Exception as e:
            print(f"Ошибка получения file_path: {e}")
    
    return files
