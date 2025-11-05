import os
import requests
import asyncpg
from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_DSN = os.getenv("POSTGRES_DSN")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mini-app-mauve-alpha.vercel.app", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.create_pool(POSTGRES_DSN)
    print("✅ Database connected")

# НОВЫЙ ЭНДПОИНТ: Получение материалов по тегу
@app.get("/api/materials/{tag}")
async def get_materials_by_tag(
    tag: str,
    course: Optional[int] = Query(None),
    group_lang: Optional[str] = Query(None)
):
    """Получает материалы по тегу с фильтрацией по курсу и группе"""
    
    query = "SELECT * FROM materials WHERE tag = $1"
    params = [tag]
    
    # Фильтр по курсу (материал доступен если course IS NULL или совпадает)
    if course is not None:
        query += f" AND (course IS NULL OR course = ${len(params)+1})"
        params.append(course)
    
    # Фильтр по группе (материал доступен если group_lang IS NULL или совпадает)
    if group_lang:
        query += f" AND (group_lang IS NULL OR group_lang = ${len(params)+1})"
        params.append(group_lang)
    
    query += " ORDER BY created_at"
    
    async with app.state.db.acquire() as conn:
        rows = await conn.fetch(query, *params)
    
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
        
        # Если есть file_id, получаем URL для скачивания через Telegram Bot API
        if row["file_id"]:
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
                print(f"❌ Error getting file URL for {row['file_id']}: {e}")
        
        materials.append(material)
    
    return {"materials": materials, "count": len(materials)}

# Старый эндпоинт (можно оставить или удалить)
@app.get("/api/files")
async def get_files():
    async with app.state.db.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, file_name, file_id FROM materials WHERE file_id IS NOT NULL ORDER BY created_at DESC LIMIT 50"
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
