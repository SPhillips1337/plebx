"""
Adapter layer for ingesting posts from different Plebbit sources.
Modes supported (placeholder): 'db' (read-only DB), 'api' (HTTP), 'ipfs' (IPFS pubsub / CID fetch).
This is a scaffold: implement connectors and auth as needed.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json

class Adapter:
    def __init__(self, mode: str = "ipfs", config: Optional[Dict[str, Any]] = None):
        self.mode = mode
        self.config = config or {}

    def fetch_recent_posts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent raw posts from the configured source.
        Placeholder implementations return sample data; replace with real connectors.
        """
        if self.mode == "db":
            return self._fetch_from_db(limit)
        if self.mode == "api":
            return self._fetch_from_api(limit)
        if self.mode == "ipfs" or self.mode == "bridge":
            return self._fetch_from_ipfs(limit)
        raise ValueError(f"Unknown adapter mode: {self.mode}")

    def _fetch_from_db(self, limit: int):
        # TODO: implement DB connector (read-only) to Plebbit database
        return self._sample_data(limit)

    def _fetch_from_api(self, limit: int):
        # TODO: implement HTTP API connector to Plebbit (if available)
        return self._sample_data(limit)

    def _fetch_from_ipfs(self, limit: int):
        # TODO: implement IPFS CID fetch / pubsub subscription
        return self._sample_data(limit)

    def normalize_post(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a raw post into the canonical PlebX schema.
        Required canonical fields: id, author_id, content, created_at (ISO8601), attachments (list), reply_to
        """
        # Best-effort normalization; adapt to your source structure
        post = {
            "id": str(raw.get("id") or raw.get("cid") or raw.get("_id")),
            "author_id": raw.get("author") or raw.get("author_id") or raw.get("user"),
            "content": raw.get("content") or raw.get("text") or "",
            "created_at": raw.get("created_at") or raw.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "attachments": raw.get("attachments") or raw.get("media") or [],
            "reply_to": raw.get("reply_to") or raw.get("in_reply_to") or None,
            "external_source": self.mode,
            "raw": raw,
        }
        return post

    def seed_sample_data(self, path: str = "data/samples.json", count: int = 5):
        samples = self._sample_data(count)
        try:
            import os
            os.makedirs("data", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(samples, f, indent=2)
            return path
        except Exception:
            return None

    def _sample_data(self, limit: int):
        now = datetime.now(timezone.utc)
        items = []
        for i in range(min(10, limit)):
            items.append({
                "id": f"sample-{i}",
                "author": f"user{i%3}",
                "content": f"This is sample post {i}",
                "created_at": (now).isoformat(),
                "attachments": [],
                "reply_to": None,
                "engagement": {"likes": i*2, "comments": i//2}
            })
        return items

if __name__ == "__main__":
    a = Adapter(mode="ipfs")
    posts = a.fetch_recent_posts(3)
    for raw in posts:
        print(json.dumps(a.normalize_post(raw), indent=2))
