import os
import requests
import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional
import uvicorn

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "")
API_BASE_URL = os.environ.get("API_BASE_URL", "")
# ДОБАВЬТЕ в начало (после импортов)
ADMIN_USER_IDS = [6720999592, 6520890849]
app = FastAPI(title="MedEkzamen API", version="1.0.0")
# ДОБАВЬТЕ после функции get_file_url()
@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    """Получить данные пользователя по Telegram ID"""
    conn = await get_db()
    try:
        user = await conn.fetchrow(
            """
            SELECT user_id, username, full_name, course, group_lang, registered_at
            FROM users
            WHERE user_id = $1
            """,
            user_id
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "course": user["course"],
                "group_lang": user["group_lang"],
                "registered_at": user["registered_at"].isoformat() if user["registered_at"] else None,
                "is_admin": user["user_id"] in ADMIN_USER_IDS
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        await conn.close()


@app.post("/api/users/")
async def create_user(request: Request):
    """Зарегистрировать нового пользователя"""
    conn = await get_db()
    try:
        data = await request.json()

        user_id = data.get("user_id")
        username = data.get("username")
        full_name = data.get("full_name")
        course = data.get("course")
        group_lang = data.get("group_lang")

        # Валидация
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        if not full_name:
            raise HTTPException(status_code=400, detail="full_name is required")
        if not course or course not in [1, 2, 3, 4, 5, 6]:
            raise HTTPException(status_code=400, detail="course must be 1-6")
        if group_lang not in ["ru", "tj"]:
            raise HTTPException(status_code=400, detail="group_lang must be 'ru' or 'tj'")

        # Вставка или обновление пользователя
        await conn.execute(
            """
            INSERT INTO users (user_id, username, full_name, course, group_lang)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                full_name = EXCLUDED.full_name,
                course = EXCLUDED.course,
                group_lang = EXCLUDED.group_lang
            """,
            user_id, username, full_name, course, group_lang
        )

        # Получаем обновленные данные
        user = await conn.fetchrow(
            """
            SELECT user_id, username, full_name, course, group_lang, registered_at
            FROM users
            WHERE user_id = $1
            """,
            user_id
        )

        return {
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "course": user["course"],
                "group_lang": user["group_lang"],
                "registered_at": user["registered_at"].isoformat() if user["registered_at"] else None,
                "is_admin": user["user_id"] in ADMIN_USER_IDS
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        await conn.close()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db():
    if not POSTGRES_DSN:
        raise HTTPException(status_code=500, detail="DB not configured")
    return await asyncpg.connect(POSTGRES_DSN, timeout=10)

def get_file_url(file_id: str) -> Optional[str]:
    if not BOT_TOKEN or not file_id:
        return None
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=5
        )
        data = r.json()
        if data.get("ok") and "result" in data:
            file_path = data["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    except:
        pass
    return None
@app.get("/api/download/{material_id}")
async def download_file(material_id: int):
    """Скачать файл с правильным именем"""
    conn = await get_db()
    try:
        material = await conn.fetchrow(
            "SELECT file_id, file_name, type FROM materials WHERE id = $1",
            material_id
        )

        if not material or not material["file_id"]:
            raise HTTPException(status_code=404, detail="File not found")

        file_id = material["file_id"]
        file_name = material["file_name"] or f"file_{material_id}"

        try:
            r = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                params={"file_id": file_id},
                timeout=5
            )
            data = r.json()

            if not data.get("ok") or "result" not in data:
                raise HTTPException(status_code=404, detail="File not found in Telegram")

            file_path = data["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

            async with httpx.AsyncClient() as client:
                response = await client.get(file_url)

                if response.status_code != 200:
                    raise HTTPException(status_code=404, detail="Failed to download file")

                content_type = response.headers.get("content-type", "application/octet-stream")

                return StreamingResponse(
                    iter([response.content]),
                    media_type=content_type,
                    headers={
                        "Content-Disposition": f'attachment; filename="{file_name}"'
                    }
                )

        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")

    finally:
        await conn.close()
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "MedEkzamen API v1.0",
        "config": {
            "bot_token": "✅ set" if BOT_TOKEN else "❌ missing",
            "database": "✅ set" if POSTGRES_DSN else "❌ missing"
        },
        "endpoints": {
            "health": "/api/health",
            "materials": "/api/materials/{tag}?course=1&group_lang=ru",
            "files": "/api/files",
            "get_user": "/api/users/{user_id}",
            "create_user": "/api/users/ (POST)"
        }
    }

@app.get("/api/health")
async def health():
    try:
        conn = await get_db()
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "postgres": version.split(",")[0]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

@app.get("/api/materials/{tag}")
async def get_materials(
    tag: str,
    course: Optional[int] = Query(None, description="Course (1-6)"),
    group_lang: Optional[str] = Query(None, description="Language group (ru/tj)")
):
    conn = await get_db()
    try:
        query = "SELECT * FROM materials WHERE tag = $1"
        params = [tag]
        
        if course is not None:
            query += f" AND (course IS NULL OR course = ${len(params)+1})"
            params.append(course)
        
        if group_lang:
            query += f" AND (group_lang IS NULL OR group_lang = ${len(params)+1})"
            params.append(group_lang)
        
        query += " ORDER BY created_at"
        rows = await conn.fetch(query, *params)
        
        materials = []
        for row in rows:
            materials.append({
                "id": row["id"],
                "tag": row["tag"],
                "type": row["type"],
                "file_id": row["file_id"],
                "file_name": row["file_name"],
                "caption": row["caption"],
                "course": row["course"],
                "group_lang": row["group_lang"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                download_url = f"{API_BASE_URL}/api/download/{row['id']}" if row["file_id"] else None
            })
        
        return {
            "success": True,
            "materials": materials,
            "count": len(materials),
            "filters": {"tag": tag, "course": course, "group_lang": group_lang}
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        await conn.close()

@app.get("/api/files")
async def get_files():
    conn = await get_db()
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
        for r in rows:
            files.append({
                "id": r["id"],
                "name": r["file_name"] or "No name",
                "tag": r["tag"],
                "type": r["type"],
                "course": r["course"],
                "group_lang": r["group_lang"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None
            })
        
        return {"success": True, "files": files, "count": len(files)}
    
    finally:
        await conn.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)







