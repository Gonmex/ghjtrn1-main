import sqlite3
import yt_dlp

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_collections (
            file_path TEXT PRIMARY KEY,
            collection_name TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def downloading(url, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])