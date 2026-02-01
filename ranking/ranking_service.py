"""
Simple ranking service prototype inspired by the twitter/the-algorithm idea.
Provides a deterministic score_post(...) function and a simple API for ranking a list of posts.
This is intentionally small and dependency-free so you can iterate quickly.
"""
from datetime import datetime, timezone
from math import log1p
from typing import Dict, Any, List, Optional

# Tunable weights
RECENCY_HALF_LIFE_SECONDS = 60 * 60 * 12  # 12 hours
LIKE_WEIGHT = 1.0
COMMENT_WEIGHT = 2.0
MEDIA_BONUS = 0.5
FOLLOW_BOOST = 1.5


def _age_seconds(iso_ts: str) -> float:
    try:
        dt = datetime.fromisoformat(iso_ts)
        return (datetime.now(timezone.utc) - dt).total_seconds()
    except Exception:
        return 0.0


def recency_score(iso_ts: str) -> float:
    age = _age_seconds(iso_ts)
    # Exponential decay: score = 2^(-age/half_life)
    try:
        return 2 ** (-age / RECENCY_HALF_LIFE_SECONDS)
    except Exception:
        return 0.0


def engagement_score(post: Dict[str, Any]) -> float:
    eng = post.get("engagement", {}) or {}
    likes = eng.get("likes", 0)
    comments = eng.get("comments", 0)
    # log-scaling so single viral posts don't dominate
    return LIKE_WEIGHT * log1p(likes) + COMMENT_WEIGHT * log1p(comments)


def score_post(post: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> float:
    """Compute a ranking score for a post for an optional user profile.
    user_profile may contain 'follows' (list of author ids) to boost followed authors.
    """
    s = 0.0
    s += recency_score(post.get("created_at", "")) * 10.0
    s += engagement_score(post)
    if post.get("attachments"):
        s += MEDIA_BONUS
    if user_profile:
        follows = set(user_profile.get("follows", []))
        if post.get("author_id") in follows:
            s *= FOLLOW_BOOST
    return s


def rank_posts(posts: List[Dict[str, Any]], user_profile: Optional[Dict[str, Any]] = None, top_k: int = 50) -> List[Dict[str, Any]]:
    scored = []
    for p in posts:
        sc = score_post(p, user_profile)
        scored.append((sc, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:top_k]]


if __name__ == "__main__":
    # quick smoke test
    sample = [
        {"id": "a", "author_id": "u1", "created_at": datetime.now(timezone.utc).isoformat(), "engagement": {"likes": 10, "comments": 2}, "attachments": []},
        {"id": "b", "author_id": "u2", "created_at": datetime.now(timezone.utc).isoformat(), "engagement": {"likes": 2, "comments": 0}, "attachments": ["img.jpg"]},
    ]
    ranked = rank_posts(sample, user_profile={"follows": ["u2"]})
    print([p["id"] for p in ranked])
