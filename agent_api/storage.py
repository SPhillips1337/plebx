import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

DB_PATH = os.environ.get("PLEBX_DB_PATH", "data/plebx.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            author_id TEXT,
            content TEXT,
            created_at TEXT,
            attachments TEXT,
            reply_to TEXT,
            engagement TEXT,
            raw TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def upsert_posts(posts: List[Dict[str, Any]]):
    conn = _conn()
    cur = conn.cursor()
    for p in posts:
        cur.execute(
            """
            INSERT INTO posts (id, author_id, content, created_at, attachments, reply_to, engagement, raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              author_id=excluded.author_id,
              content=excluded.content,
              created_at=excluded.created_at,
              attachments=excluded.attachments,
              reply_to=excluded.reply_to,
              engagement=excluded.engagement,
              raw=excluded.raw
            """,
            (
                p.get("id"),
                p.get("author_id"),
                p.get("content"),
                p.get("created_at"),
                json.dumps(p.get("attachments") or []),
                p.get("reply_to"),
                json.dumps(p.get("engagement") or {}),
                json.dumps(p.get("raw") or {}),
            ),
        )
    conn.commit()
    conn.close()


def get_recent_posts(limit: int = 50) -> List[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT id, author_id, content, created_at, attachments, reply_to, engagement, raw FROM posts ORDER BY datetime(created_at) DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append(
            {
                "id": r[0],
                "author_id": r[1],
                "content": r[2],
                "created_at": r[3],
                "attachments": json.loads(r[4]) if r[4] else [],
                "reply_to": r[5],
                "engagement": json.loads(r[6]) if r[6] else {},
                "raw": json.loads(r[7]) if r[7] else {},
            }
        )
    return out


def get_post_and_thread(post_id: str) -> Optional[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT id, author_id, content, created_at, attachments, reply_to, engagement, raw FROM posts WHERE id = ?", (post_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    post = {
        "id": row[0],
        "author_id": row[1],
        "content": row[2],
        "created_at": row[3],
        "attachments": json.loads(row[4]) if row[4] else [],
        "reply_to": row[5],
        "engagement": json.loads(row[6]) if row[6] else {},
        "raw": json.loads(row[7]) if row[7] else {},
    }
    # Build a thread tree by loading posts and mapping replies -> children
    cur.execute("SELECT id, author_id, content, created_at, attachments, reply_to, engagement, raw FROM posts ORDER BY datetime(created_at) ASC")
    rows = cur.fetchall()

    def row_to_post(r):
        return {
            "id": r[0],
            "author_id": r[1],
            "content": r[2],
            "created_at": r[3],
            "attachments": json.loads(r[4]) if r[4] else [],
            "reply_to": r[5],
            "engagement": json.loads(r[6]) if r[6] else {},
            "raw": json.loads(r[7]) if r[7] else {},
        }

    posts_by_id = {}
    children_map = {}
    for r in rows:
        p = row_to_post(r)
        posts_by_id[p["id"]] = p
        parent = p.get("reply_to")
        children_map.setdefault(parent, []).append(p)

    # Recursive builder: attach 'replies' list to each node
    def build_tree(node_id):
        children = []
        for child in children_map.get(node_id) or []:
            # deep copy minimal fields and attach replies
            c = dict(child)
            c["replies"] = build_tree(child["id"])
            children.append(c)
        return children

    thread = build_tree(post_id)

    conn.close()
    return {"post": post, "thread": thread}
