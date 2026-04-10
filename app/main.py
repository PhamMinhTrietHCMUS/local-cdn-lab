import json
import os
import socket

import psycopg2
import redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Media API")
HOSTNAME = socket.gethostname()  # container ID — dùng để phân biệt replica
CACHE_KEY = "media:random_image"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "10"))

# ── Prometheus metrics: tự động đo request count, latency, in-progress ──
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)

def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "mediadb"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASS", "secret"),
    )

@app.on_event("startup")
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS images (id SERIAL PRIMARY KEY, url TEXT NOT NULL)")
    cur.execute("INSERT INTO images (url) SELECT 'https://picsum.photos/800/600' WHERE NOT EXISTS (SELECT 1 FROM images)")
    conn.commit(); cur.close(); conn.close()

@app.get("/")
def health():
    return {"status": "healthy", "service": "media-api", "hostname": HOSTNAME}

@app.get("/image")
def serve_image():
    try:
        cached = redis_client.get(CACHE_KEY)
        if cached:
            payload = json.loads(cached)
            payload["hostname"] = HOSTNAME
            payload["cache"] = "hit"
            return payload
    except Exception:
        # Fallback to DB path if Redis is temporarily unavailable.
        pass

    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT id, url FROM images ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone(); cur.close(); conn.close()

    if not row:
        return JSONResponse({"error": "no images"}, 404)

    payload = {"id": row[0], "url": row[1], "hostname": HOSTNAME, "cache": "miss"}
    try:
        redis_client.setex(CACHE_KEY, CACHE_TTL_SECONDS, json.dumps({"id": row[0], "url": row[1]}))
    except Exception:
        pass
    return payload
