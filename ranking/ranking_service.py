"""
Ranking service for PlebX - integrates with P2P bridge
Computes content scores using Twitter-style algorithm with recency, engagement, and follows.
"""
import asyncio
from datetime import datetime, timezone
from math import log1p
from typing import Dict, Any, List, Optional

# Tunable weights (inspired by twitter/the-algorithm)
RECENCY_HALF_LIFE_SECONDS = 60 * 60 * 12  # 12 hours
LIKE_WEIGHT = 1.0
COMMENT_WEIGHT = 2.0
MEDIA_BONUS = 0.5
FOLLOW_BOOST = 1.5

class RankingService:
    """Service for ranking posts from Plebbit network via P2P bridge"""
    
    def __init__(self, bridge_api_url: str = "http://localhost:8001"):
        self.bridge_api_url = bridge_api_url
        self.user_profiles = {}  # Cache user profiles for follows
    
    async def get_user_profile(self, author_address: str) -> Optional[Dict[str, Any]]:
        """Get user profile from bridge or cache"""
        # Try to get from bridge first
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"{self.bridge_api_url}/users/{author_address}"
                async with session.get(url) as response:
                    if response.status == 200:
                        profile = await response.json()
                        self.user_profiles[author_address] = profile
                        return profile
        except Exception:
            pass
        
        # Return cached profile or default
        return self.user_profiles.get(author_address, {
            "address": author_address,
            "display_name": f"User {author_address[:8]}",
            "follows": []
        })
    
    async def rank_posts_from_bridge(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch posts from P2P bridge and rank them"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Get posts from popular subplebbits
                url = f"{self.bridge_api_url}/subs/memes.eth/posts?limit={limit}&sort=hot"
                async with session.get(url) as response:
                    if response.status == 200:
                        posts = await response.json()
                        return await self.rank_posts(posts)
        except Exception as e:
            print(f"Error ranking posts: {e}")
            return []
    
    async def rank_posts(self, posts: List[Dict[str, Any]], user_address: Optional[str] = None) -> List[Dict[str, Any]]:
        """Rank a list of posts with user-specific scoring"""
        scored_posts = []
        
        for post in posts:
            # Get user profile for follow boost
            author_address = post.get("author", {}).get("address", "")
            user_profile = await self.get_user_profile(author_address)
            
            # Calculate ranking score
            score = await self._calculate_score(post, user_profile)
            
            scored_post = {
                **post,
                "ranking_score": score,
                "ranked_at": datetime.now(timezone.utc).isoformat()
            }
            scored_posts.append(scored_post)
        
        # Sort by score (descending)
        scored_posts.sort(key=lambda x: x["ranking_score"], reverse=True)
        return scored_posts
    
    async def _calculate_score(self, post: Dict[str, Any], user_profile: Optional[Dict[str, Any]]) -> float:
        """Calculate ranking score for individual post"""
        base_score = 0.0
        
        # Recency score (newer posts get higher score)
        created_at = post.get("timestamp", 0)
        age_score = self._recency_score(created_at)
        base_score += age_score
        
        # Engagement score
        engagement = post.get("engagement", {})
        likes = engagement.get("upvote_count", 0)
        comments = engagement.get("reply_count", 0)
        
        base_score += LIKE_WEIGHT * log1p(likes + 1)
        base_score += COMMENT_WEIGHT * log1p(comments + 1)
        
        # Media bonus
        if post.get("attachments") and len(post.get("attachments", [])) > 0:
            base_score += MEDIA_BONUS
        
        # Follow boost (user sees followed authors higher)
        if user_profile:
            user_follows = set(user_profile.get("follows", []))
            if post.get("author", {}).get("address") in user_follows:
                base_score *= FOLLOW_BOOST
        
        return base_score
    
    def _recency_score(self, created_at: int) -> float:
        """Calculate recency score with exponential decay"""
        try:
            dt = datetime.fromtimestamp(created_at, timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - dt).total_seconds()
            return 2 ** (-age_seconds / RECENCY_HALF_LIFE_SECONDS)
        except:
            return 0.0
    
    async def get_ranked_feed(self, user_address: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Get ranked feed for user"""
        posts = await self.rank_posts_from_bridge(limit)
        
        return {
            "posts": posts,
            "user_address": user_address,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "algorithm": "recency + engagement + follows + media_bonus"
        }


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
