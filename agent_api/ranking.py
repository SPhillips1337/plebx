from typing import List, Dict, Any
from datetime import datetime, timezone

class RankingService:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    def score_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Applies a simplified ranking algorithm based on recency and engagement.
        Score = (Likes * 2 + Comments * 5) / (AgeInHours + 2)^1.5
        """
        scored_posts = []
        now = datetime.now(timezone.utc)

        for post in posts:
            engagement = post.get("engagement") or {}
            likes = engagement.get("likes", 0)
            comments = engagement.get("comments", 0)

            created_at_str = post.get("created_at")
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                created_at = now

            age_hours = (now - created_at).total_seconds() / 3600

            # Simple scoring formula
            score = (likes * 2 + comments * 5 + 1) / ((age_hours + 2) ** 1.5)

            scored_post = post.copy()
            scored_post["score"] = score
            scored_posts.append(scored_post)

        # Sort by score descending
        scored_posts.sort(key=lambda x: x["score"], reverse=True)
        return scored_posts
