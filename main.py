import os
import asyncpg
import httpx # Используем асинхронный клиент вместо requests
import asyncio # Для параллельного выполнения запросов
from fastapi import FastAPI, HTTPException, Request, Query # Импортируем Query для тегов
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_DSN = os.getenv("POSTGRES_DSN")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mini-app-mauve-alpha.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- DB HANDLER --------------------

async def get_db():
    """Создаёт пул подключений (ленивая инициализация) или возвращает существующий."""
    if not POSTGRES_DSN:
        print("❌ POSTGRES_DSN не установлен. Проверьте переменные окружения.")
        raise ConnectionError("POSTGRES_DSN not configured.")
        
    if not hasattr(app.state, "db"):
        try:
            # Пытаемся создать пул, устанавливаем таймаут подключения
            app.state.db = await asyncpg.create_pool(POSTGRES_DSN, timeout=5.0) 
            print("✅ Database pool initialized")
        except Exception as e:
            # Логируем точную ошибку при инициализации
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА DB STARTUP: {e}")
            raise ConnectionError(f"DB connection failed on init: {e}")

    return app.state.db

# -------------------- TELEGRAM UTILITY --------------------

async def fetch_file_url(client: httpx.AsyncClient, file_id: str, file_name: str, bot_token: str) -> Dict[str, str] | None:
    """Асинхронно получает URL файла из Telegram."""
    if not file_id:
        return None
        
    try:
        # Используем асинхронный client.get
        r = await client.get(f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}", timeout=5.0)
        r.raise_for_status() 
        
        data = r.json()
        
        if data.get("ok") and "result" in data:
            file_path = data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            return {"name": file_name or "Без названия", "url": download_url}
            
    except Exception as e:
        print(f"⚠️ Ошибка получения file_path для file_id {file_id}: {e}")
        
    return None

# -------------------- ENDPOINT --------------------

@app.get("/api/files")
# Добавлены два параметра: tag и course
async def get_files(
    request: Request, 
    tag: Optional[str] = Query(None, description="Tag for filtering materials (e.g., chem1)"),
    course: Optional[int] = Query(None, description="Course number for filtering (e.g., 3)") # Принимаем курс как int
):
    
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="BOT_TOKEN is not configured.")

    db_rows = []
    
    try:
        db = await get_db()
        
        # --- Динамическое построение SQL-запроса с фильтрацией ---
        sql_query_parts = ["SELECT id, file_name, file_id FROM materials WHERE file_id IS NOT NULL"]
        sql_args = []
        param_index = 1
        
        # 1. Фильтрация по ТЕГУ (Предмет)
        if tag:
            sql_query_parts.append(f" AND tag = ${param_index}")
            sql_args.append(tag)
            param_index += 1
            
        # 2. Фильтрация по КУРСУ (если курс передан)
        if course is not None:
            # course_id - это ID курса, который, вероятно, хранится в materials.course_id
            # Используем course_id, так как в таблице course - это число.
            sql_query_parts.append(f" AND course_id = ${param_index}")
            sql_args.append(course)
            param_index += 1
        
        # Собираем финальный запрос
        sql_query = " ".join(sql_query_parts)
        sql_query += " ORDER BY created_at DESC LIMIT 50"
        # ---------------------------------------------------------
        
        async with db.acquire() as conn:
            # Выполняем запрос с аргументами
            db_rows = await conn.fetch(sql_query, *sql_args)
            
    except ConnectionError as e:
        # Ошибка, пойманная из get_db()
        raise HTTPException(status_code=500, detail=f"DB Connection Error: {e}")
    except asyncpg.exceptions.PostgresError as e:
        # Ошибка в SQL-запросе (например, неверное имя таблицы)
        print(f"❌ SQL Query Error: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed. SQL Error: {e}")
    except Exception as e:
        import traceback
        print("🔥 Неизвестная ошибка:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


    # --- Параллельное получение ссылок на скачивание ---
    files = []
    if db_rows:
        async with httpx.AsyncClient() as client:
            tasks = []
            for row in db_rows:
                # Создаем задачу для каждого файла
                tasks.append(
                    fetch_file_url(client, row["file_id"], row["file_name"], BOT_TOKEN)
                )
            
            # Запускаем все задачи одновременно и ждем их завершения
            results = await asyncio.gather(*tasks)
            
            # Фильтруем пустые результаты
            files = [res for res in results if res is not None]

    return files
