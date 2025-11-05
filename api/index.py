import os
import json
from typing import Optional

# Переменные окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "")

# ==================== ПРОСТАЯ ПРОВЕРКА ====================

def handler(event, context):
    """Простейший handler для тестирования"""
    
    path = event.get("rawPath", "/")
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    
    # Корневой маршрут
    if path == "/" or path == "/api" or path == "/api/":
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "status": "ok",
                "message": "MedEkzamen API is running",
                "config": {
                    "bot_token": "set" if BOT_TOKEN else "missing",
                    "database": "set" if POSTGRES_DSN else "missing"
                }
            })
        }
    
    # Любой другой путь
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "path": path,
            "method": method,
            "message": "Endpoint works"
        })
    }
