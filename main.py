import os
import requests
import asyncpg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "")

app = FastAPI(title="MedEkzamen API", version="1.0.0")

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
            "files": "/api/files"
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
                "download_url": get_file_url(row["file_id"]) if row["file_id"] else None
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
