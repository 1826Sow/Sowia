"""Local conversation storage."""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
DB_PATH=Path("data/sowia.db")
def _connect():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)")
    return conn
def save_message(session_id,role,content):
    with _connect() as conn: conn.execute("INSERT INTO messages(session_id,role,content,created_at) VALUES(?,?,?,?)",(session_id,role,content,datetime.now(timezone.utc).isoformat()))
def get_history(session_id,limit=30):
    with _connect() as conn: rows=conn.execute("SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",(session_id,limit)).fetchall()
    return [{"role":r,"content":c} for r,c in reversed(rows)]
def clear_history(session_id):
    with _connect() as conn: conn.execute("DELETE FROM messages WHERE session_id=?",(session_id,))
