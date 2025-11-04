import os
import requests
import asyncpg
import httpx  # <-- 1. Заменили requests на httpx
import asyncio # <-- 2. Импортируем asyncio для параллельных запросов

from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_DSN = os.getenv("POSTGRES_DSN")


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

# --- Вспомогательная асинхронная функция ---
async def fetch_file_url(client: httpx.AsyncClient, file_id: str, file_name: str) -> dict | None:
    """Асинхронно получает URL файла из Telegram."""
    if not file_id:
        return None
        
    try:
        # 3. Используем асинхронный client.get
        r = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}")
        r.raise_for_status() # Проверка на ошибки (404, 500 и т.д.)
        
        data = r.json()
        
        if data.get("ok") and "result" in data:
            file_path = data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            return {"name": file_name or "Без названия", "url": download_url}
            
    except Exception as e:
        # Логируем ошибку, но не останавливаем весь процесс
        print(f"Ошибка получения file_path для file_id {file_id}: {e}")
        
    return None

@app.get("/api/files")
async def get_files(request: Request):
    
    db_rows = []
    async with app.state.db.acquire() as conn:
        # 4. Оптимизировали запрос: добавили WHERE file_id IS NOT NULL
        db_rows = await conn.fetch(
            "SELECT id, file_name, file_id FROM materials "
            "WHERE file_id IS NOT NULL " # <-- Важное добавление
            "ORDER BY created_at DESC LIMIT 50"
        )
    
    files = []
    
    # 5. Используем httpx.AsyncClient для всех запросов
    async with httpx.AsyncClient() as client:
        # 6. Создаем список задач (coroutine) для параллельного выполнения
        tasks = []
        for row in db_rows:
            tasks.append(
                fetch_file_url(client, row["file_id"], row["file_name"])
            )
        
        # 7. Запускаем все задачи одновременно и ждем их завершения
        results = await asyncio.gather(*tasks)
        
        # 8. Фильтруем пустые результаты (None), если были ошибки
        files = [res for res in results if res is not None]
    
    return files
