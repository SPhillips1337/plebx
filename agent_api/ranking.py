from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone

class RankingService:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    def score_posts(self, posts: List[Dict[str, Any]], viewer_following: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
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
            replies = engagement.get("replies", 0) or engagement.get("comments", 0)

            created_at_str = post.get("created_at")
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                created_at = now

            age_hours = (now - created_at).total_seconds() / 3600

            # Improved scoring formula
            # base engagement signal with diminishing returns for likes and replies
            eng = (likes * 1.8) + (comments * 5.0) + ( (replies or 0) * 2.5 )
            base = (eng + 1.0)
            score = base / ((age_hours + 2.0) ** 1.4)

            # Personalization: boost posts from authors the viewer follows
            if viewer_following and post.get("author_id") in viewer_following:
                score *= 1.6

            scored_post = post.copy()
            scored_post["score"] = score
            scored_posts.append(scored_post)

        # Sort by score descending
        scored_posts.sort(key=lambda x: x["score"], reverse=True)
        return scored_posts
