import os
import requests
import asyncpg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# Переменные окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "")

# FastAPI приложение
app = FastAPI(title="MedEkzamen API", version="1.0.0")

# CORS - разрешаем запросы с фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def get_db_connection():
    """Создаёт подключение к PostgreSQL"""
    if not POSTGRES_DSN:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN not configured")
    try:
        conn = await asyncpg.connect(POSTGRES_DSN, timeout=10)
        return conn
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

def get_telegram_file_url(file_id: str) -> Optional[str]:
    """Получает прямую ссылку на файл через Telegram Bot API"""
    if not BOT_TOKEN or not file_id:
        return None
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=5
        )
        data = response.json()
        if data.get("ok") and "result" in data:
            file_path = data["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    except Exception as e:
        print(f"Error getting file URL: {e}")
    return None

# ==================== МАРШРУТЫ ====================

@app.get("/")
async def root():
    """Корневой эндпоинт - проверка работоспособности"""
    return {
        "status": "ok",
        "message": "MedEkzamen API is running",
        "version": "1.0.0",
        "config": {
            "bot_token": "✅ configured" if BOT_TOKEN else "❌ missing",
            "database": "✅ configured" if POSTGRES_DSN else "❌ missing"
        },
        "endpoints": {
            "health": "/api/health",
            "materials": "/api/materials/{tag}?course=1&group_lang=ru",
            "files": "/api/files"
        }
    }

@app.get("/api/health")
async def health_check():
    """Проверка подключения к базе данных"""
    try:
        conn = await asyncpg.connect(POSTGRES_DSN, timeout=5)
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "postgres_version": version.split(",")[0]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

@app.get("/api/materials/{tag}")
async def get_materials_by_tag(
    tag: str,
    course: Optional[int] = Query(None, description="Курс (1-6)"),
    group_lang: Optional[str] = Query(None, description="Язык группы (ru/tj)")
):
    """
    Получает материалы по тегу с фильтрацией
    
    Примеры:
    - /api/materials/chem1?course=1&group_lang=ru
    - /api/materials/lecture_bio1?course=1&group_lang=tj
    - /api/materials/summary1.1?course=1
    """
    
    conn = await get_db_connection()
    
    try:
        # Строим SQL запрос с фильтрами
        query = "SELECT * FROM materials WHERE tag = $1"
        params = [tag]
        
        # Фильтр по курсу (материал доступен если course IS NULL или совпадает)
        if course is not None:
            query += f" AND (course IS NULL OR course = ${len(params)+1})"
            params.append(course)
        
        # Фильтр по языку группы
        if group_lang:
            query += f" AND (group_lang IS NULL OR group_lang = ${len(params)+1})"
            params.append(group_lang)
        
        query += " ORDER BY created_at ASC"
        
        # Выполняем запрос
        rows = await conn.fetch(query, *params)
        
        # Формируем список материалов
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
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "download_url": None
            }
            
            # Получаем прямую ссылку на файл, если есть file_id
            if row["file_id"]:
                material["download_url"] = get_telegram_file_url(row["file_id"])
            
            materials.append(material)
        
        return {
            "success": True,
            "materials": materials,
            "count": len(materials),
            "filters": {
                "tag": tag,
                "course": course,
                "group_lang": group_lang
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        await conn.close()

@app.get("/api/files")
async def get_all_files():
    """Получает список всех файлов из БД (для отладки)"""
    
    conn = await get_db_connection()
    
    try:
        rows = await conn.fetch(
            """
            SELECT id, file_name, file_id, tag, type, course, group_lang, created_at 
            FROM materials 
            WHERE file_id IS NOT NULL 
            ORDER BY created_at DESC 
            LIMIT 100
            """
        )
        
        files = []
        for row in rows:
            files.append({
                "id": row["id"],
                "name": row["file_name"] or "Без названия",
                "tag": row["tag"],
                "type": row["type"],
                "course": row["course"],
                "group_lang": row["group_lang"],
                "file_id": row["file_id"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
        
        return {
            "success": True,
            "files": files,
            "count": len(files)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        await conn.close()

# ==================== VERCEL SERVERLESS HANDLER ====================
from mangum import Mangum
handler = Mangum(app, lifespan="off")
