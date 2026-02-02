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


def get_post_and_thread(post_id: str, depth: int = 3, page: int = 1, per_page: int = 20) -> Optional[Dict[str, Any]]:
    """Return the post and a paginated, depth-limited thread.

    - depth: how many levels of replies to include (1 = direct replies only).
    - page / per_page: paginate the top-level replies (those replying directly to post_id).
    """
    # enforce sane limits
    MAX_DEPTH = 6
    MAX_PER_PAGE = 200
    depth = max(0, min(int(depth), MAX_DEPTH))
    per_page = max(1, min(int(per_page), MAX_PER_PAGE))
    page = max(1, int(page))

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

    # Load all posts (small DB assumption). We will paginate top-level replies only.
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

    # Build replies recursively with depth limit
    def build_replies_for(node_id, depth_remaining):
        if depth_remaining <= 0:
            return []
        out = []
        for child in children_map.get(node_id) or []:
            c = dict(child)
            # attach nested replies
            c["replies"] = build_replies_for(child["id"], depth_remaining - 1)
            out.append(c)
        return out

    top_children = children_map.get(post_id, []) or []
    total_top = len(top_children)
    start = (page - 1) * per_page
    end = start + per_page
    paged_children = top_children[start:end]

    # For each paged child, build nested replies up to (depth-1)
    thread = []
    for child in paged_children:
        node = dict(child)
        node["replies"] = build_replies_for(child["id"], depth - 1)
        thread.append(node)

    conn.close()

    meta = {"page": page, "per_page": per_page, "total_top_replies": total_top, "depth": depth}
    return {"post": post, "thread": thread, "meta": meta}


def get_stats() -> Dict[str, Any]:
    """Return simple DB stats: post_count, db_path, file_size, last_modified (iso)."""
    import os
    stats = {"post_count": 0, "db_path": DB_PATH, "file_size": None, "last_modified": None}
    if not os.path.exists(DB_PATH):
        return stats
    try:
        conn = _conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM posts")
        row = cur.fetchone()
        stats["post_count"] = int(row[0]) if row else 0
        conn.close()
    except Exception:
        # best-effort
        stats["post_count"] = 0

    try:
        st = os.stat(DB_PATH)
        stats["file_size"] = st.st_size
        stats["last_modified"] = datetime.utcfromtimestamp(st.st_mtime).isoformat() + "Z"
    except Exception:
        pass

    return stats
