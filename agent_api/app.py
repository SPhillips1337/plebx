from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import os
import re
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from adapter import Adapter
from ranking import RankingService
from storage import init_db, upsert_posts, get_recent_posts, get_post_and_thread

# Optional Redis support
try:
    import redis
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

app = FastAPI()


@app.on_event("startup")
def startup_event():
    # initialize sqlite DB for simple persistence/cache
    try:
        init_db()
    except Exception as e:
        print("init_db failed:", e)

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


@app.get("/feed")
async def feed(mode: str = "ipfs", limit: int = 20):
    adapter = Adapter(mode=mode)
    ranking = RankingService()

    if mode == "db":
        posts = get_recent_posts(limit=limit)
    else:
        raw_posts = adapter.fetch_recent_posts(limit=limit)
        normalized_posts = [adapter.normalize_post(p) for p in raw_posts]
        # cache into DB for later use
        try:
            upsert_posts(normalized_posts)
        except Exception:
            pass
        posts = normalized_posts

    scored_posts = ranking.score_posts(posts)

    return {"ok": True, "posts": scored_posts, "count": len(scored_posts)}


@app.get("/post/{post_id}")
async def get_post(post_id: str, mode: str = "ipfs"):
    adapter = Adapter(mode=mode)
    if mode == "db":
        res = get_post_and_thread(post_id)
        if not res:
            raise HTTPException(status_code=404, detail="Post not found")
        return {"ok": True, "post": res["post"], "thread": res["thread"]}

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

    # If dry_run or writeback disabled, return preview
    if req.dry_run or not ENABLE_WRITEBACK:
        return {"ok": True, "dry_run": True, "record": record}

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
