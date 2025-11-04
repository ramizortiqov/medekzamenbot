import os
import requests
import asyncpg
from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_DSN = os.getenv("POSTGRES_DSN")  # <--- обязательно проверь, что эта переменная есть в Vercel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mini-app-mauve-alpha.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db():
    """Создаёт пул подключений, если ещё не создан"""
    if not hasattr(app.state, "db"):
        app.state.db = await asyncpg.create_pool(POSTGRES_DSN)
        print("✅ Database pool initialized")
    return app.state.db


@app.get("/api/files")
async def get_files(request: Request):
    try:
        db = await get_db()
        async with db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, file_name, file_id FROM materials ORDER BY created_at DESC LIMIT 50"
            )

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

    except Exception as e:
        import traceback
        print("🔥 Ошибка в /api/files:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
