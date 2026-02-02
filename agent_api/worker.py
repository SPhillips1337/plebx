import os
import time
import json
import uuid
from typing import Optional

from storage import _conn, upsert_posts

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
REVIEW_QUEUE_KEY = os.environ.get("REVIEW_QUEUE_KEY", "plebx:publish:queue")
FILE_QUEUE = os.path.join(os.path.dirname(__file__), "..", "data", "publish_queue.jsonl")

try:
    import redis
    r = redis.from_url(REDIS_URL)
except Exception:
    r = None


def process_envelope(envelope: dict):
    # normalized post structure
    try:
        post = {
            "id": f"worker-{uuid.uuid4().hex[:8]}",
            "author_id": envelope.get("user") or envelope.get("author") or "unknown",
            "content": envelope.get("content"),
            "created_at": envelope.get("timestamp") or envelope.get("created_at") or None,
            "attachments": envelope.get("attachments") or [],
            "reply_to": envelope.get("reply_to") or None,
            "engagement": {},
            "raw": envelope,
        }
        upsert_posts([post])
        print("worker: persisted post", post["id"])
    except Exception as e:
        print("worker: failed to process envelope", e)


def process_file_queue(path: str):
    if not os.path.exists(path):
        return
    # read all lines and truncate file
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            return
        # process each line
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                env = json.loads(line)
                process_envelope(env)
            except Exception as e:
                print("worker: failed to parse line", e)
        # truncate file
        with open(path, "w", encoding="utf-8") as f:
            pass
    except Exception as e:
        print("worker: file queue error", e)


def run_loop():
    print("worker: starting")
    while True:
        # first process any file queue entries
        try:
            process_file_queue(FILE_QUEUE)
        except Exception as e:
            print("worker: file processing failed", e)

        # then block on redis if available
        if r:
            try:
                item = r.brpop(REVIEW_QUEUE_KEY, timeout=5)
                if item and len(item) >= 2:
                    payload = item[1]
                    try:
                        env = json.loads(payload)
                        process_envelope(env)
                    except Exception as e:
                        print("worker: invalid redis payload", e)
                else:
                    time.sleep(0.2)
            except Exception as e:
                print("worker: redis error", e)
                time.sleep(1.0)
        else:
            # no redis, just sleep and reprocess file periodically
            time.sleep(2.0)


if __name__ == "__main__":
    run_loop()
