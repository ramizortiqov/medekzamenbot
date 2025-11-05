import os
import requests
import asyncpg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from mangum import Mangum  # <<<< ВАЖНО: адаптер для serverless

# Загружаем переменные окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
POSTGRES_DSN = os.environ.get("POSTGRES_DSN")

app = FastAPI(title="MedEkzamen API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене замените на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальный пул подключений
db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    if not POSTGRES_DSN:
        print("⚠️ WARNING: POSTGRES_DSN not set!")
        return
    try:
        db_pool = await asyncpg.create_pool(
            POSTGRES_DSN, 
            min_size=1, 
            max_size=3,
            command_timeout=60
        )
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()
        print("🔌 Database disconnected")

# ==================== МАРШРУТЫ ====================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "MedEkzamen API is running",
        "bot_token_set": bool(BOT_TOKEN),
        "db_connected": bool(db_pool),
        "endpoints": {
            "materials": "/api/materials/{tag}",
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
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    query = "SELECT * FROM materials WHERE tag = $1"
    params = [tag]
    
    if course is not None:
        query += f" AND (course IS NULL OR course = ${len(params)+1})"
        params.append(course)
    
    if group_lang:
        query += f" AND (group_lang IS NULL OR group_lang = ${len(params)+1})"
        params.append(group_lang)
    
    query += " ORDER BY created_at"
    
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
    except Exception as e:
        print(f"❌ Database query error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
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
                print(f"⚠️ Error getting file URL: {e}")
        
        materials.append(material)
    
    print(f"✅ Found {len(materials)} materials for tag={tag}")
    return {"materials": materials, "count": len(materials)}

@app.get("/api/files")
async def get_files():
    """Получает список всех файлов (для отладки)"""
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, file_name, file_id, tag FROM materials WHERE file_id IS NOT NULL ORDER BY created_at DESC LIMIT 50"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    files = []
    for row in rows:
        files.append({
            "id": row["id"],
            "name": row["file_name"] or "Без названия",
            "tag": row["tag"],
            "file_id": row["file_id"]
        })
    
    return {"files": files, "count": len(files)}

# <<<< ВАЖНО: Адаптер для Vercel Serverless
handler = Mangum(app)
