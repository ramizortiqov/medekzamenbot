import os
import requests
import asyncpg
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_DSN= os.getenv("POSTGRES_DSN")

if not BOT_TOKEN or not POSTGRES_DSN:
    raise ValueError("BOT_TOKEN and POSTGRES_DSN must be set in .env file")

app = FastAPI()

# Убедитесь, что здесь указан домен вашего фронтенда на Vercel
# Можно добавить и localhost для локальной разработки
allowed_origins = [
    "https://mini-app-mauve-alpha.vercel.app",
    "http://localhost:5500", # Пример для Live Server в VS Code
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    """Инициализация пула подключений к базе данных при старте приложения."""
    try:
        app.state.db = await asyncpg.create_pool(POSTGRES_DSN)
        print("✅ Database pool connected successfully.")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        # Вы можете остановить запуск, если база недоступна
        raise HTTPException(status_code=500, detail="Database connection failed")

@app.get("/api/files")
async def get_files_by_tag(tag: str):
    """
    Получает материалы из базы данных, отфильтрованные по тегу.
    Формирует прямые ссылки на файлы Telegram и возвращает данные
    в формате, совместимом с фронтендом.
    """
    if not tag:
        raise HTTPException(status_code=400, detail="Tag parameter is required")

    print(f"🔍 Received request for tag: {tag}")

    async with app.state.db.acquire() as conn:
        # 1. SQL-запрос теперь выбирает ВСЕ нужные поля и фильтрует по тегу
        rows = await conn.fetch(
            "SELECT id, tag, type, file_name, file_id, caption FROM materials WHERE tag = $1 ORDER BY id",
            tag
        )

    if not rows:
        print(f"✅ No materials found for tag: {tag}")
        return [] # Возвращаем пустой массив, если ничего не найдено

    materials = []
    for row in rows:
        file_url = None
        file_id = row["file_id"]
        material_type = row["type"]

        # 2. Получаем ссылку на файл, только если это не просто текст
        if material_type != 'text' and file_id:
            try:
                # Используем сессию для улучшения производительности
                with requests.Session() as s:
                    r = s.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}")
                    r.raise_for_status() # Проверка на ошибки HTTP (4xx, 5xx)
                    data = r.json()

                if data.get("ok"):
                    file_path = data["result"]["file_path"]
                    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                else:
                    print(f"⚠️ Telegram API error for file_id {file_id}: {data.get('description')}")
            except requests.RequestException as e:
                print(f"❌ HTTP Error getting file_path for {file_id}: {e}")
            except Exception as e:
                print(f"❌ Unexpected error processing file_id {file_id}: {e}")

        # 3. Собираем объект в формате, который ожидает фронтенд
        materials.append({
            "id": row["id"],
            "tag": row["tag"],
            "type": material_type,
            "file_url": file_url,
            "file_name": row["file_name"],
            "caption": row["caption"]
        })

    print(f"✅ Found and processed {len(materials)} materials for tag: {tag}")
    return materials

# Добавим корневой эндпоинт для проверки, что API работает
@app.get("/")
def read_root():
    return {"status": "MedEkzamen API is running!"}
