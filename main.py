import os
import asyncpg
import httpx # Асинхронный HTTP-клиент
import asyncio # Для параллельных запросов к Telegram
from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# -------------------- 1. НАСТРОЙКА --------------------

# Загружаем переменные окружения из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_DSN = os.getenv("POSTGRES_DSN")


app = FastAPI()

# Разрешаем фронтенду (Vercel Mini App) обращаться к API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mini-app-mauve-alpha.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- 2. ПОДКЛЮЧЕНИЕ К БД --------------------

@app.on_event("startup")
async def startup():
    """Создание пула подключений к PostgreSQL при запуске сервера."""
    if not POSTGRES_DSN:
        raise ValueError("POSTGRES_DSN environment variable is not set.")
    try:
        app.state.db = await asyncpg.create_pool(POSTGRES_DSN)
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        # Вы можете остановить приложение, если соединение с БД критично
        # raise Exception("Failed to connect to database.")


# -------------------- 3. ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ --------------------

async def fetch_file_url(client: httpx.AsyncClient, file_id: str, file_name: str, bot_token: str) -> dict | None:
    """Асинхронно получает URL файла из Telegram с помощью httpx."""
    if not file_id:
        return None
        
    try:
        # Используем httpx.AsyncClient
        r = await client.get(f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}")
        r.raise_for_status() # Проверка на HTTP-ошибки (4xx, 5xx)
        
        data = r.json()
        
        if data.get("ok") and "result" in data:
            file_path = data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            return {"name": file_name or "Без названия", "url": download_url}
            
    except Exception as e:
        # Логируем ошибку, чтобы не блокировать другие файлы
        print(f"Ошибка получения file_path для file_id {file_id}: {e}")
        
    return None

# -------------------- 4. ОСНОВНОЙ ЭНДПОИНТ --------------------

@app.get("/api/files")
# Добавляем Optional[str] = None для приема параметра 'tag'
async def get_files(request: Request, tag: Optional[str] = None):
    
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="BOT_TOKEN is not configured.")

    db_rows = []
    
    # --- Динамическое построение SQL-запроса ---
    sql_query = "SELECT id, file_name, file_id FROM materials WHERE file_id IS NOT NULL"
    sql_args = []
    
    # ФИЛЬТРАЦИЯ ПО ТЕГУ
    if tag:
        # Используем параметризованный запрос для безопасности (asyncpg использует $1, $2, ...)
        sql_query += " AND tag = $1"
        sql_args.append(tag)
    
    sql_query += " ORDER BY created_at DESC LIMIT 50"
    # ------------------------------------------

    try:
        async with app.state.db.acquire() as conn:
            # Выполняем запрос с аргументами
            db_rows = await conn.fetch(sql_query, *sql_args)
    except Exception as e:
        print(f"❌ Ошибка при выполнении запроса к БД: {e}")
        raise HTTPException(status_code=500, detail="Database query failed.")


    files = []
    
    # --- Параллельное выполнение запросов к Telegram ---
    # Создаем асинхронный клиент для всех запросов
    async with httpx.AsyncClient(timeout=10.0) as client: 
        tasks = []
        for row in db_rows:
            # Создаем задачу для каждого файла
            tasks.append(
                fetch_file_url(client, row["file_id"], row["file_name"], BOT_TOKEN)
            )
        
        # Запускаем все задачи одновременно и ждем их завершения
        results = await asyncio.gather(*tasks)
        
        # Фильтруем пустые результаты (None), которые вернулись при ошибке
        files = [res for res in results if res is not None]
    
    return files
