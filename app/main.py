import os, socket, psycopg2
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Media API")
HOSTNAME = socket.gethostname()  # container ID — dùng để phân biệt replica

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
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT id, url FROM images ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone(); cur.close(); conn.close()
    return {"id": row[0], "url": row[1], "hostname": HOSTNAME} if row else JSONResponse({"error": "no images"}, 404)
