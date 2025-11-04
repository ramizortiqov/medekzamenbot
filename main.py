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

# ... (весь импортированный код, включая httpx, asyncpg и т.д.) ...

@app.get("/api/files")
async def get_files(request: Request, tag: Optional[str] = None):
    # 1. Проверяем, что запрос доходит досюда и возвращает статический ответ
    return [
        {"name": "Тестовый файл 1", "url": "http://test.url/1"},
        {"name": "Тестовый файл 2", "url": "http://test.url/2"}
    ]

# ... (Временное закомментирование всего, что использует app.state.db и httpx) ...
