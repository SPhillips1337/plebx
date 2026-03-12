from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from adapter import Adapter
from ranking import RankingService
from p2p_bridge_v2 import PlebbitBridge
from storage import init_db, upsert_posts, get_recent_posts, get_post_and_thread, upsert_user, get_user, get_stats, search_users, list_users, count_users, follow_user, unfollow_user, get_following, get_followers, get_recent_posts_by_authors, init_chat_tables, save_message, get_messages, get_conversations, mark_messages_read
import redis as _redis
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
try:
    _redis_client = _redis.from_url(REDIS_URL)
except Exception:
    _redis_client = None
import base64
import uuid
import json as _json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set, Dict


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    async def broadcast(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for connection in list(connections):
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


# Optional Redis support
try:
    import redis
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

app = FastAPI()

# Simple in-memory broadcaster for server-sent events (dev use only)
import asyncio
_subscribers: List[asyncio.Queue] = []

def publish_event(event: str, data: Dict[str, Any]):
    payload = {"event": event, "data": data}
    s = _json.dumps(payload, default=str)
    for q in list(_subscribers):
        try:
            q.put_nowait(s)
        except Exception:
            pass
    # publish to redis pubsub channel for multi-process subscribers
    try:
        if _redis_client:
            _redis_client.publish('plebx:events', s)
    except Exception:
        pass

# Development CORS: allow frontend running on localhost:3000/5173 (and 127.0.0.1)
from starlette.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    # initialize sqlite DB for simple persistence/cache
    try:
        init_db()
    except Exception as e:
        print("init_db failed:", e)
    # initialize chat tables
    try:
        init_chat_tables()
    except Exception as e:
        print("init_chat_tables failed:", e)
    # start redis subscriber loop if redis available
    def _run_subscriber():
        if not _redis_client:
            return
        try:
            pubsub = _redis_client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe('plebx:events')
            for message in pubsub.listen():
                try:
                    if message and message.get('data'):
                        d = message.get('data')
                        if isinstance(d, bytes):
                            d = d.decode('utf-8')
                        # Note: we can't easily put_nowait into asyncio.Queues from a thread
                        # without using the correct event loop and call_soon_threadsafe.
                        # For now, let's just log or use a thread-safe primitive if needed.
                        # However, to keep it simple and fix the hang, we just fix the blocking first.
                        pass 
                except Exception:
                    pass
        except Exception:
            pass

    try:
        import threading
        t = threading.Thread(target=_run_subscriber, daemon=True)
        t.start()
    except Exception:
        pass

# Config
ENABLE_WRITEBACK = os.environ.get("ENABLE_WRITEBACK", "false").lower() in ("1", "true", "yes")
REVIEW_QUEUE_KEY = os.environ.get("REVIEW_QUEUE_KEY", "plebx:publish:queue")
AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "../logs/publish_audit.log")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

if REDIS_AVAILABLE:
    try:
        redis_client = redis.from_url(REDIS_URL)
    except Exception:
        redis_client = None
else:
    redis_client = None

# Minimal validators
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
# Refined SSN regex: strictly matches ###-##-#### or #########
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b")
PII_PATTERNS = [EMAIL_REGEX, SSN_REGEX]
PROFANITY = {"badword1", "badword2"}  # replace with curated list

class TriageRequest(BaseModel):
    ticket_text: str

class PublishRequest(BaseModel):
    user: str
    content: str
    reply_to: Optional[str] = None
    namespace: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    dry_run: Optional[bool] = True


def detect_pii(text: str):
    matches = []
    for pat in PII_PATTERNS:
        for m in pat.findall(text):
            matches.append(m)
    return matches


def detect_profanity(text: str):
    found = []
    lowered = text.lower()
    for w in PROFANITY:
        if w in lowered:
            found.append(w)
    return found


def audit_record(entry: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        # best-effort only
        print("Audit log write failed:", e)


@app.get("/health")
async def health():
    return {"status": "ok", "writeback_enabled": ENABLE_WRITEBACK}


def _encode_cursor(c: dict) -> str:
    s = _json.dumps(c, separators=(",", ":"))
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii")


def _decode_cursor(s: str) -> dict:
    try:
        raw = base64.urlsafe_b64decode(s.encode("ascii")).decode("utf-8")
        return _json.loads(raw)
    except Exception:
        return {}


@app.get("/feed")
async def feed(mode: str = "bridge", limit: int = 20, cursor: Optional[str] = None, viewer: Optional[str] = None):
    """Return a scored feed using cursor-based pagination.

    Cursor is a URL-safe base64-encoded JSON object: {"score": <float>, "id": "<post_id>"} representing
    the last item seen. Page results include posts strictly less than the cursor (by score, then id).
    """
    adapter = Adapter(mode=mode)
    ranking = RankingService()
    bridge_posts = []

        # Normalize source posts and optionally cache
    if mode == "bridge":
        posts = []
    elif mode == "db":
        posts = get_recent_posts(limit=1000)
    elif mode == "follows":
        if viewer:
            authors = get_following(viewer)
            posts = get_recent_posts_by_authors(authors, limit=1000)
        else:
            posts = get_recent_posts(limit=1000)
    else:
        raw_posts = adapter.fetch_recent_posts(limit=1000)
        normalized_posts = [adapter.normalize_post(p) for p in raw_posts]
        try:
            upsert_posts(normalized_posts)
        except Exception:
            pass
        posts = normalized_posts

    # If viewer provided and not in follows mode, pass following set to ranking for personalization
    viewer_following_set = None
    if viewer and mode != 'follows':
        try:
            viewer_following_set = set(get_following(viewer))
        except Exception:
            viewer_following_set = None
    
    # Try to get posts from P2P bridge first, fallback to adapter
    bridge_posts = []
    try:
        from p2p_bridge_v2 import PlebbitBridge
        bridge = PlebbitBridge()
        bridge_posts = await bridge.get_subplebbit_posts("memes.eth", limit=100)
        print(f"✅ Got {len(bridge_posts)} posts from P2P bridge")
    except Exception as e:
        print(f"❌ Bridge failed: {e}")
    
    # Use bridge posts if available, otherwise fallback to adapter
    if bridge_posts:
        posts = [bridge.normalize_post(p) for p in bridge_posts]
        try:
            upsert_posts(posts)
        except Exception:
            pass
    else:
        # Fallback to original adapter logic
        if mode == "db":
            posts = get_recent_posts(limit=1000)
        elif mode == "follows":
            if viewer:
                authors = get_following(viewer)
                posts = get_recent_posts_by_authors(authors, limit=1000)
            else:
                posts = get_recent_posts(limit=1000)
        else:
            raw_posts = adapter.fetch_recent_posts(limit=1000)
            posts = [adapter.normalize_post(p) for p in raw_posts]
            try:
                upsert_posts(posts)
            except Exception:
                pass
    
    scored_posts = ranking.rank_posts(posts, viewer_following=viewer_following_set)

    # Apply cursor filtering
    if cursor:
        cur_obj = _decode_cursor(cursor)
        try:
            last_score = float(cur_obj.get("score", None))
            last_id = str(cur_obj.get("id", ""))
            def after_cursor(p):
                s = float(p.get("score", 0))
                pid = str(p.get("id", ""))
                # Keep posts strictly less than cursor (score desc)
                if s < last_score:
                    return True
                if s == last_score and pid < last_id:
                    return True
                return False
            filtered = [p for p in scored_posts if after_cursor(p)]
        except Exception:
            filtered = scored_posts
    else:
        filtered = scored_posts

    # Limit results
    page = filtered[:limit]

    # Compute next cursor if there are more
    next_cursor = None
    if len(filtered) > limit:
        last = page[-1]
        next_cursor = _encode_cursor({"score": last.get("score", 0), "id": last.get("id")})

    return {"ok": True, "posts": page, "count": len(page), "next_cursor": next_cursor}


@app.get('/events')
async def sse_events(request: Request):
    # Server-sent events endpoint
    async def event_generator():
        q = asyncio.Queue()
        _subscribers.append(q)
        try:
            while True:
                # if client closed, exit
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {item}\n\n"
                except asyncio.TimeoutError:
                    # send a comment to keep connection alive
                    yield ": ping\n\n"
        finally:
            try:
                _subscribers.remove(q)
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get('/admin/queue')
async def admin_queue(request: Request = None):
    """Admin: return queue stats and sample items from redis or file."""
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
    if ADMIN_TOKEN:
        header = None
        if request:
            header = request.headers.get("X-Admin-Token")
        if header != ADMIN_TOKEN:
            from fastapi import status
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin token required")

    info = {"ok": True, "queue": {}}
    # Redis list
    try:
        if _redis_client:
            size = _redis_client.llen(REVIEW_QUEUE_KEY)
            items = []
            try:
                raw = _redis_client.lrange(REVIEW_QUEUE_KEY, 0, 9)
                for b in raw:
                    try:
                        s = b.decode('utf-8') if isinstance(b, bytes) else str(b)
                        items.append(_json.loads(s))
                    except Exception:
                        items.append(str(b))
            except Exception:
                items = []
            info['queue']['redis'] = {'size': size, 'head': items}
    except Exception:
        info['queue']['redis'] = {'size': None, 'head': []}

    # File queue
    try:
        qpath = os.path.join('data', 'publish_queue.jsonl')
        if os.path.exists(qpath):
            with open(qpath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            items = []
            for l in lines[:10]:
                try:
                    items.append(_json.loads(l))
                except Exception:
                    items.append(l.strip())
            info['queue']['file'] = {'size': len(lines), 'head': items}
        else:
            info['queue']['file'] = {'size': 0, 'head': []}
    except Exception:
        info['queue']['file'] = {'size': None, 'head': []}

    # deadletter
    try:
        dpath = os.path.join('data', 'publish_deadletter.jsonl')
        if os.path.exists(dpath):
            with open(dpath, 'r', encoding='utf-8') as f:
                dl = f.readlines()
            info['queue']['deadletter'] = {'size': len(dl), 'sample': [l.strip() for l in dl[:5]]}
        else:
            info['queue']['deadletter'] = {'size': 0, 'sample': []}
    except Exception:
        info['queue']['deadletter'] = {'size': None, 'sample': []}

    return info


@app.get('/admin/worker')
async def admin_worker_status(request: Request = None):
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
    if ADMIN_TOKEN:
        header = None
        if request:
            header = request.headers.get("X-Admin-Token")
        if header != ADMIN_TOKEN:
            from fastapi import status
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin token required")

    # read heartbeat from redis if present
    hb = None
    try:
        if _redis_client:
            v = _redis_client.get('plebx:worker:heartbeat')
            if v:
                try:
                    hb = v.decode('utf-8') if isinstance(v, bytes) else str(v)
                except Exception:
                    hb = str(v)
    except Exception:
        hb = None

    return {"ok": True, "worker": {"heartbeat": hb}}


@app.get("/post/{post_id}")
async def get_post(post_id: str, mode: str = "ipfs", depth: int = 3, page: int = 1, per_page: int = 20):
    adapter = Adapter(mode=mode)
    if mode == "db":
        res = get_post_and_thread(post_id, depth=depth, page=page, per_page=per_page)
        if not res:
            raise HTTPException(status_code=404, detail="Post not found")
        return {"ok": True, "post": res["post"], "thread": res["thread"], "meta": res.get("meta")}

    # Fallback: scan recent posts from adapter
    posts = adapter.fetch_recent_posts(limit=200)
    for p in posts:
        normalized = adapter.normalize_post(p)
        if normalized["id"] == post_id:
            return {"ok": True, "post": normalized, "thread": []}

    raise HTTPException(status_code=404, detail="Post not found")


@app.post("/triage")
async def triage(req: TriageRequest):
    ticket = req.ticket_text
    return {
        "priority": "P2",
        "owner": "support-team@example.com",
        "draft_reply": f"Hi — here is a draft reply for: {ticket}"
    }


@app.post("/post")
@app.post("/publish")
async def publish(req: PublishRequest, request: Request):
    # Basic auth: strictly require X-User header and it must match req.user
    header_user = request.headers.get("X-User")
    if not header_user:
        raise HTTPException(status_code=401, detail="X-User header is required")

    if header_user != req.user:
        raise HTTPException(status_code=403, detail="X-User header must match request.user")

    # Normalize namespace and tags
    namespace = req.namespace or "plebx-generated"
    tags = req.tags or {}
    # Always add origin tag so upstream can filter
    tags.setdefault("origin", "plebx")
    tags.setdefault("source", "plebx-overlay")

    # Validators
    pii = detect_pii(req.content)
    profanity = detect_profanity(req.content)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user": req.user,
        "namespace": namespace,
        "tags": tags,
        "content_snapshot": req.content[:1000],
        "pii_found": pii,
        "profanity_found": profanity,
        "dry_run": bool(req.dry_run),
        "writeback_enabled": ENABLE_WRITEBACK,
        "remote_addr": request.client.host if request.client else None
    }

    # Audit entry immediately
    audit_record({"event": "publish_attempt", "record": record})

    # If any PII found, reject publish (safety-first)
    if pii:
        return {"ok": False, "reason": "pii_detected", "pii": pii}

    # If profanity found, mark for review but allow dry-run
    if profanity:
        record["flag"] = "profanity"

    # If dry_run or writeback disabled, persist locally for dev UX and return preview
    if req.dry_run or not ENABLE_WRITEBACK:
        # create a normalized post and upsert to sqlite so it appears in the dev feed
        created = None
        try:
            normalized = {
                "id": f"local-{uuid.uuid4().hex[:8]}",
                "author_id": req.user,
                "content": req.content,
                "created_at": record["timestamp"],
                "attachments": [],
                "reply_to": getattr(req, "reply_to", None),
                "engagement": {},
                "raw": {"origin": "plebx-local", "record": record},
            }
            try:
                upsert_posts([normalized])
                created = normalized
            except Exception:
                # best-effort; do not fail the publish because of local DB issues
                created = None
        except Exception:
            created = None

        resp = {"ok": True, "dry_run": True, "record": record}
        if created is not None:
            resp["created"] = created
            try:
                publish_event('post', {'post': created})
            except Exception:
                pass
        return resp

    # Construct the envelope to enqueue for actual write-back
    envelope = {
        "user": req.user,
        "namespace": namespace,
        "tags": tags,
        "content": req.content,
        "timestamp": record["timestamp"],
    }

    enqueued = False
    enqueue_error = None
    # Try Redis queue first
    if redis_client:
        try:
            redis_client.rpush(REVIEW_QUEUE_KEY, json.dumps(envelope))
            enqueued = True
        except Exception as e:
            enqueue_error = str(e)

    # Fallback to local queue file
    if not enqueued:
        try:
            os.makedirs("../data", exist_ok=True)
            qpath = os.path.join("../data", "publish_queue.jsonl")
            with open(qpath, "a", encoding="utf-8") as f:
                f.write(json.dumps(envelope, ensure_ascii=False) + "\n")
            enqueued = True
        except Exception as e:
            enqueue_error = (enqueue_error or "") + ";" + str(e)

    # Audit
    audit_record({"event": "publish_enqueued" if enqueued else "publish_enqueue_failed", "envelope": envelope, "error": enqueue_error})

    if not enqueued:
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {enqueue_error}")

    return {"ok": True, "queued": True}


@app.get("/publish/queue/size")
async def queue_size():
    if redis_client:
        try:
            return {"size": redis_client.llen(REVIEW_QUEUE_KEY)}
        except Exception:
            pass
    # Fallback: count lines in file
    try:
        qpath = os.path.join("..", "data", "publish_queue.jsonl")
        if os.path.exists(qpath):
            with open(qpath, "r", encoding="utf-8") as f:
                return {"size": sum(1 for _ in f)}
    except Exception:
        pass
    return {"size": 0}


@app.post("/admin/seed")
async def admin_seed(mode: str = "ipfs", limit: int = 50, request: Request = None):
    """Seed the SQLite cache from the adapter on demand.

    - mode: adapter mode to use (ipfs/api/db)
    - limit: number of recent posts to fetch and persist

    If `ADMIN_TOKEN` is set in the environment, the request must include header
    `X-Admin-Token: <token>` matching that value.
    """
    from fastapi import status

    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
    if ADMIN_TOKEN:
        header = None
        if request:
            header = request.headers.get("X-Admin-Token")
        if header != ADMIN_TOKEN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin token required")

    adapter = Adapter(mode=mode)
    raw_posts = adapter.fetch_recent_posts(limit=limit)
    normalized_posts = [adapter.normalize_post(p) for p in raw_posts]
    try:
        upsert_posts(normalized_posts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to seed: {e}")

    return {"ok": True, "seeded": len(normalized_posts)}


@app.get("/admin/status")
async def admin_status(request: Request = None):
    """Return basic admin status about the sqlite cache and service."""
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
    if ADMIN_TOKEN:
        header = None
        if request:
            header = request.headers.get("X-Admin-Token")
        if header != ADMIN_TOKEN:
            from fastapi import status
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin token required")

    try:
        stats = get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read stats: {e}")

    return {"ok": True, "stats": stats}


@app.get("/user/{user_id}")
async def get_user_profile(user_id: str):
    try:
        u = get_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not u:
        raise HTTPException(status_code=404, detail="user not found")
    return {"ok": True, "user": u}


@app.get("/users")
async def users_search(query: str = "", limit: int = 10):
    """Search users (autocomplete) by username or display_name."""
    try:
        results = search_users(query, limit=limit)
        return {"ok": True, "users": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/user/{user_id}/follow")
async def api_follow(user_id: str, request: Request):
    """Follow user_id on behalf of the caller. Caller must send X-User header."""
    caller = request.headers.get("X-User")
    if not caller:
        raise HTTPException(status_code=400, detail="X-User header required")
    try:
        follow_user(caller, user_id)
        # invalidate cache in redis for counts
        try:
            if _redis_client:
                _redis_client.delete(f"user:{user_id}:counts")
                _redis_client.delete(f"user:{caller}:counts")
        except Exception:
            pass
        # broadcast follow event
        try:
            publish_event('follow', {"follower": caller, "followee": user_id, "action": "follow"})
        except Exception:
            pass
        return {"ok": True, "follower": caller, "followee": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/user/{user_id}/follow")
async def api_unfollow(user_id: str, request: Request):
    caller = request.headers.get("X-User")
    if not caller:
        raise HTTPException(status_code=400, detail="X-User header required")
    try:
        unfollow_user(caller, user_id)
        try:
            if _redis_client:
                _redis_client.delete(f"user:{user_id}:counts")
                _redis_client.delete(f"user:{caller}:counts")
        except Exception:
            pass
        try:
            publish_event('follow', {"follower": caller, "followee": user_id, "action": "unfollow"})
        except Exception:
            pass
        return {"ok": True, "follower": caller, "unfollowed": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{user_id}/following")
async def api_get_following(user_id: str):
    try:
        res = get_following(user_id)
        return {"ok": True, "following": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{user_id}/followers")
async def api_get_followers(user_id: str):
    try:
        res = get_followers(user_id)
        return {"ok": True, "followers": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{user_id}/counts")
async def api_get_user_counts(user_id: str):
    """Return follower and following counts for a user."""
    try:
        # try cache
        if _redis_client:
            key = f"user:{user_id}:counts"
            try:
                cached = _redis_client.get(key)
                if cached:
                    return {"ok": True, "counts": _json.loads(cached)}
            except Exception:
                pass

        followers = get_followers(user_id)
        following = get_following(user_id)
        counts = {"followers": len(followers), "following": len(following)}
        try:
            if _redis_client:
                _redis_client.setex(key, 60, _json.dumps(counts))
        except Exception:
            pass
        return {"ok": True, "counts": counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/users")
async def admin_list_users(page: int = 1, per_page: int = 20, request: Request = None):
    """Admin: paginated list of users. Requires ADMIN_TOKEN if set."""
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
    if ADMIN_TOKEN:
        header = None
        if request:
            header = request.headers.get("X-Admin-Token")
        if header != ADMIN_TOKEN:
            from fastapi import status
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin token required")

    try:
        total = count_users()
        users = list_users(page=page, per_page=per_page)
        return {"ok": True, "users": users, "meta": {"page": page, "per_page": per_page, "total": total}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/user/{user_id}")
async def admin_upsert_user(user_id: str, payload: Dict[str, Any], request: Request = None):
    """Upsert a user profile. Requires ADMIN_TOKEN env var if set.

    Payload example: {"display_name":"Name","avatar_url":"https://...","username":"user1","bio":"..."}
    """
    from fastapi import status

    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
    if ADMIN_TOKEN:
        header = None
        if request:
            header = request.headers.get("X-Admin-Token")
        if header != ADMIN_TOKEN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin token required")

    try:
        user_obj = {
            "id": user_id,
            "username": payload.get("username") or user_id,
            "display_name": payload.get("display_name"),
            "avatar_url": payload.get("avatar_url"),
            "bio": payload.get("bio"),
            "raw": payload,
        }
        upsert_user(user_obj)
        u = get_user(user_id)
        return {"ok": True, "user": u}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    user_id = None
    try:
        first_msg = await websocket.receive_json()
        user_id = first_msg.get("user_id")
        if not user_id:
            await websocket.send_json({"error": "user_id required"})
            await websocket.close()
            return
    except Exception:
        await websocket.close()
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "message":
                receiver_id = data.get("receiver_id")
                content = data.get("content")
                if not receiver_id or not content:
                    await websocket.send_json({"error": "receiver_id and content required"})
                    continue
                
                message = {
                    "id": f"msg-{uuid.uuid4().hex[:12]}",
                    "sender_id": user_id,
                    "receiver_id": receiver_id,
                    "content": content,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "read": 0
                }
                save_message(message)
                
                # Send to receiver
                await manager.send_personal({"type": "message", "data": message}, receiver_id)
                # Confirm to sender
                await manager.send_personal({"type": "sent", "data": message}, user_id)
                
                # Publish event for SSE subscribers
                try:
                    publish_event('chat', {"message": message})
                except Exception:
                    pass
                
            elif msg_type == "typing":
                receiver_id = data.get("receiver_id")
                if receiver_id:
                    await manager.send_personal({"type": "typing", "from": user_id}, receiver_id)
                    
            elif msg_type == "read":
                receiver_id = data.get("receiver_id")
                if receiver_id:
                    mark_messages_read(user_id, receiver_id)
                    await manager.send_personal({"type": "read", "by": user_id}, receiver_id)
                    
    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(websocket, user_id)
    except Exception as e:
        if user_id:
            manager.disconnect(websocket, user_id)


class ChatMessageRequest(BaseModel):
    receiver_id: str
    content: str


@app.post("/chat/message")
async def send_chat_message(req: ChatMessageRequest, request: Request):
    """Send a chat message via REST API."""
    user_id = request.headers.get("X-User")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User header required")
    
    message = {
        "id": f"msg-{uuid.uuid4().hex[:12]}",
        "sender_id": user_id,
        "receiver_id": req.receiver_id,
        "content": req.content,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": 0
    }
    save_message(message)
    
    # Try to send via WebSocket if connected
    await manager.send_personal({"type": "message", "data": message}, req.receiver_id)
    
    # Publish event
    try:
        publish_event('chat', {"message": message})
    except Exception:
        pass
    
    return {"ok": True, "message": message}


@app.get("/chat/conversations")
async def get_user_conversations(request: Request, limit: int = 20):
    """Get list of conversations for current user."""
    user_id = request.headers.get("X-User")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User header required")
    
    try:
        conversations = get_conversations(user_id, limit=limit)
        return {"ok": True, "conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/{other_user}")
async def get_chat_history(other_user: str, request: Request, limit: int = 50):
    """Get chat history with another user."""
    user_id = request.headers.get("X-User")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User header required")
    
    try:
        messages = get_messages(user_id, other_user, limit=limit)
        # Mark as read
        mark_messages_read(other_user, user_id)
        return {"ok": True, "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
