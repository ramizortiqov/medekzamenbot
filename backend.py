import os
import requests
import asyncpg
from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_DSN = "postgresql://ramiz:unppr78026@amvera-ramizortiqov-cnpg-medekzamendb-rw:5432/bot_database"

app = FastAPI()

# Разрешаем фронтенду (Vercel) подключаться
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

@app.get("/api/files")
async def get_files(request: Request):
    async with app.state.db.acquire() as conn:
        rows = await conn.fetch("SELECT id, file_name, file_id FROM materials ORDER BY created_at DESC LIMIT 50")
    
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

# 🔽 Добавляем этот блок в самом конце файла:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000)
