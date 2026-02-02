import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

DB_PATH = os.environ.get("PLEBX_DB_PATH", "/data/plebx.db")


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
    # Indexes to speed up common queries (reply lookups and ordering by created_at)
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_reply_to ON posts(reply_to)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at)")
    except Exception:
        # best-effort; some SQLite builds may behave differently
        pass
    conn.commit()
    conn.close()
    # Ensure users table exists as well
    try:
        init_users_table()
    except Exception:
        pass


def init_users_table():
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT,
            display_name TEXT,
            avatar_url TEXT,
            bio TEXT,
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

    # After posts are upserted, optionally upsert simple user profiles derived from posts
    for p in posts:
        try:
            raw = p.get("raw") or {}
            author_id = p.get("author_id")
            profile = None
            # look for common profile shapes
            if isinstance(raw, dict):
                profile = raw.get("author_profile") or raw.get("author_meta")
                # fallback fields
                if not profile:
                    display = raw.get("author_display_name") or raw.get("author_name")
                    avatar = raw.get("author_avatar") or raw.get("author_avatar_url")
                    if display or avatar:
                        profile = {"id": author_id, "display_name": display, "avatar_url": avatar}
            if profile:
                try:
                    upsert_user({
                        "id": profile.get("id") or author_id,
                        "username": profile.get("username") or author_id,
                        "display_name": profile.get("display_name") or profile.get("name"),
                        "avatar_url": profile.get("avatar_url") or profile.get("avatar"),
                        "bio": profile.get("bio"),
                        "raw": profile,
                    })
                except Exception:
                    pass
        except Exception:
            pass


def get_recent_posts(limit: int = 50) -> List[Dict[str, Any]]:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT id, author_id, content, created_at, attachments, reply_to, engagement, raw FROM posts ORDER BY datetime(created_at) DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        post = {
            "id": r[0],
            "author_id": r[1],
            "content": r[2],
            "created_at": r[3],
            "attachments": json.loads(r[4]) if r[4] else [],
            "reply_to": r[5],
            "engagement": json.loads(r[6]) if r[6] else {},
            "raw": json.loads(r[7]) if r[7] else {},
        }
        # attach author profile if available
        try:
            user = get_user(post.get("author_id"))
            post["author"] = user
        except Exception:
            post["author"] = None
        out.append(post)
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
    try:
        post["author"] = get_user(post.get("author_id"))
    except Exception:
        post["author"] = None

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

    # attach author profiles for all loaded posts
    for pid, post in posts_by_id.items():
        try:
            post["author"] = get_user(post.get("author_id"))
        except Exception:
            post["author"] = None

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


def upsert_user(user: Dict[str, Any]):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (id, username, display_name, avatar_url, bio, raw)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          username=excluded.username,
          display_name=excluded.display_name,
          avatar_url=excluded.avatar_url,
          bio=excluded.bio,
          raw=excluded.raw
        """,
        (
            user.get("id"),
            user.get("username"),
            user.get("display_name"),
            user.get("avatar_url"),
            user.get("bio"),
            json.dumps(user.get("raw") or {}),
        ),
    )
    conn.commit()
    conn.close()


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    if not user_id:
        return None
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, display_name, avatar_url, bio, raw FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "display_name": row[2],
        "avatar_url": row[3],
        "bio": row[4],
        "raw": json.loads(row[5]) if row[5] else {},
    }


def search_users(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search users by username or display_name using a case-insensitive LIKE match."""
    if not query:
        return []
    q = f"%{query}%"
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, display_name, avatar_url, bio, raw FROM users WHERE LOWER(username) LIKE LOWER(?) OR LOWER(display_name) LIKE LOWER(?) ORDER BY username LIMIT ?",
        (q, q, limit),
    )
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "username": r[1],
            "display_name": r[2],
            "avatar_url": r[3],
        })
    return out


def count_users() -> int:
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(1) FROM users")
        row = cur.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def list_users(page: int = 1, per_page: int = 20) -> List[Dict[str, Any]]:
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20
    offset = (page - 1) * per_page
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, display_name, avatar_url, bio FROM users ORDER BY username LIMIT ? OFFSET ?", (per_page, offset))
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "username": r[1],
            "display_name": r[2],
            "avatar_url": r[3],
        })
    return out
