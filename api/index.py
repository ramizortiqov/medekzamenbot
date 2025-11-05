import os
import requests
import asyncpg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from contextlib import asynccontextmanager

# Переменные окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
POSTGRES_DSN = os.environ.get("POSTGRES_DSN")

# <<<< ГЛОБАЛЬНЫЙ ПУЛ ПОДКЛЮЧЕНИЙ (создаётся при первом запросе)
db_pool = None

async def get_db_pool():
    """Ленивая инициализация пула подключений к БД"""
    global db_pool
    if db_pool is None:
        if not POSTGRES_DSN:
            raise Exception("POSTGRES_DSN not set in environment variables")
        try:
            db_pool = await asyncpg.create_pool(
                POSTGRES_DSN,
                min_size=1,
                max_size=3,
                command_timeout=60
            )
            print("✅ Database pool created")
        except Exception as e:
            print(f"❌ Failed to create database pool: {e}")
            raise
    return db_pool

# <<<< LIFESPAN CONTEXT (правильный способ для современного FastAPI)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting up...")
    try:
        await get_db_pool()
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize DB pool on startup: {e}")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    global db_pool
    if db_pool:
        await db_pool.close()
        print("🔌 Database pool closed")

# Создаём приложение с lifespan
app = FastAPI(title="MedEkzamen API", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== МАРШРУТЫ ====================

@app.get("/")
async def root():
    """Проверка работоспособности API"""
    global db_pool
    return {
        "status": "ok",
        "message": "MedEkzamen API is running",
        "bot_token_set": bool(BOT_TOKEN),
        "postgres_dsn_set": bool(POSTGRES_DSN),
        "db_pool_active": db_pool is not None,
        "endpoints": {
            "materials": "/api/materials/{tag}?course=1&group_lang=ru",
            "files": "/api/files"
        }
    }

@app.get("/api/materials/{tag}")
async def get_materials_by_tag(
    tag: str,
    course: Optional[int] = Query(None),
    group_lang: Optional[str] = Query(None)
):
    """Получает материалы по тегу с фильтрацией"""
    
    # <<<< ПОЛУЧАЕМ ПУЛ (создастся автоматически, если ещё нет)
    try:
        pool = await get_db_pool()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")
    
    # Строим запрос
    query = "SELECT * FROM materials WHERE tag = $1"
    params = [tag]
    
    if course is not None:
        query += f" AND (course IS NULL OR course = ${len(params)+1})"
        params.append(course)
    
    if group_lang:
        query += f" AND (group_lang IS NULL OR group_lang = ${len(params)+1})"
        params.append(group_lang)
    
    query += " ORDER BY created_at"
    
    # Выполняем запрос
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
    except Exception as e:
        print(f"❌ Database query error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Формируем ответ
    materials = []
    for row in rows:
        material = {
            "id": row["id"],
            "tag": row["tag"],
            "type": row["type"],
            "file_id": row["file_id"],
            "file_name": row["file_name"],
            "caption": row["caption"],
            "course": row["course"],
            "group_lang": row["group_lang"],
            "download_url": None
        }
        
        # Получаем URL файла через Telegram Bot API
        if row["file_id"] and BOT_TOKEN:
            try:
                r = requests.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                    params={"file_id": row["file_id"]},
                    timeout=5
                )
                data = r.json()
                if data.get("ok") and "result" in data:
                    file_path = data["result"]["file_path"]
                    material["download_url"] = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            except Exception as e:
                print(f"⚠️ Error getting file URL for {row['file_id']}: {e}")
        
        materials.append(material)
    
    print(f"✅ Found {len(materials)} materials for tag={tag}, course={course}, group={group_lang}")
    return {"materials": materials, "count": len(materials)}

@app.get("/api/files")
async def get_files():
    """Получает список всех файлов (для отладки)"""
    
    try:
        pool = await get_db_pool()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")
    
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, file_name, file_id, tag, type FROM materials WHERE file_id IS NOT NULL ORDER BY created_at DESC LIMIT 50"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    files = []
    for row in rows:
        file_info = {
            "id": row["id"],
            "name": row["file_name"] or "Без названия",
            "tag": row["tag"],
            "type": row["type"],
            "file_id": row["file_id"]
        }
        
        # Опционально получаем URL
        if BOT_TOKEN:
            try:
                r = requests.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                    params={"file_id": row["file_id"]},
                    timeout=5
                )
                data = r.json()
                if data.get("ok") and "result" in data:
                    file_path = data["result"]["file_path"]
                    file_info["url"] = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            except Exception as e:
                print(f"⚠️ Error getting file URL: {e}")
        
        files.append(file_info)
    
    return {"files": files, "count": len(files)}

# <<<< ОБРАБОТЧИК ДЛЯ VERCEL SERVERLESS
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")  # lifespan управляется вручную
except ImportError:
    # Если mangum не установлен (локальная разработка)
    handler = None
