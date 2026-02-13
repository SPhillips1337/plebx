"""
Plebx P2P Bridge Service - Updated
Connects to Plebbit/Bitsocial network via plebbit-js API
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import subprocess
import os
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PlebbitPost:
    """Canonical post structure from Plebbit network"""
    cid: str
    author: Dict[str, Any]  # Author object
    subplebbit_address: str
    timestamp: int
    content: Optional[str] = None
    title: Optional[str] = None
    link: Optional[str] = None
    link_width: Optional[int] = None
    link_height: Optional[int] = None
    thumbnail_url: Optional[str] = None
    thumbnail_url_width: Optional[int] = None
    thumbnail_url_height: Optional[int] = None
    spoiler: bool = False
    flair: Optional[Dict[str, Any]] = None
    depth: int = 0  # 0 = post, 1+ = comment
    parent_cid: Optional[str] = None
    post_cid: Optional[str] = None  # Only for comments
    pinned: bool = False
    locked: bool = False
    removed: bool = False
    reply_count: int = 0
    upvote_count: int = 0
    downvote_count: int = 0
    
    @classmethod
    def from_plebbit_json(cls, data: Dict[str, Any]) -> "PlebbitPost":
        """Create PlebbitPost from plebbit-js JSON response"""
        return cls(
            cid=data.get("cid", ""),
            author=data.get("author", {}),
            subplebbit_address=data.get("subplebbitAddress", ""),
            timestamp=data.get("timestamp", 0),
            content=data.get("content"),
            title=data.get("title"),
            link=data.get("link"),
            link_width=data.get("linkWidth"),
            link_height=data.get("linkHeight"),
            thumbnail_url=data.get("thumbnailUrl"),
            thumbnail_url_width=data.get("thumbnailUrlWidth"),
            thumbnail_url_height=data.get("thumbnailUrlHeight"),
            spoiler=data.get("spoiler", False),
            flair=data.get("flair"),
            depth=data.get("depth", 0),
            parent_cid=data.get("parentCid"),
            post_cid=data.get("postCid"),
            pinned=data.get("pinned", False),
            locked=data.get("locked", False),
            removed=data.get("removed", False),
            reply_count=data.get("replyCount", 0),
            upvote_count=data.get("upvoteCount", 0),
            downvote_count=data.get("downvoteCount", 0),
        )

@dataclass
class PlebbitSub:
    """Subplebbit/board information"""
    address: str
    title: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    rules: Optional[List[str]] = None
    flairs: Optional[Dict[str, Any]] = None
    suggested: Optional[Dict[str, Any]] = None
    last_post_cid: Optional[str] = None
    roles: Optional[Dict[str, Any]] = None

class PlebbitBridge:
    """Bridge service connecting PlebX to Plebbit network via HTTP API"""
    
    def __init__(self, api_base: str = "http://localhost:9138"):
        self.api_base = api_base
        self.session = requests.Session()
        self.posts_cache = {}  # sub_address -> [posts]
        
    async def _api_call(self, endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Any:
        """Make HTTP API call to Plebbit daemon"""
        url = f"{self.api_base}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=10)
            else:
                response = self.session.post(url, json=data, timeout=10)
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"API call failed: {method} {url} - {e}")
            raise
    
    async def get_subplebbit(self, address: str) -> Optional[PlebbitSub]:
        """Get specific subplebbit info"""
        try:
            result = await self._api_call(f"/subplebbit/{address}")
            
            if result:
                return PlebbitSub(
                    address=result.get("address", address),
                    title=result.get("title"),
                    description=result.get("description"),
                    created_at=result.get("createdAt"),
                    updated_at=result.get("updatedAt"),
                    features=result.get("features"),
                    rules=result.get("rules"),
                    flairs=result.get("flairs"),
                    suggested=result.get("suggested"),
                    last_post_cid=result.get("lastPostCid"),
                    roles=result.get("roles")
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get subplebbit {address}: {e}")
            return None
    
    async def get_comment(self, cid: str) -> Optional[PlebbitPost]:
        """Get a comment/post by CID"""
        try:
            result = await self._api_call(f"/comment/{cid}")
            
            if result:
                return PlebbitPost.from_plebbit_json(result)
            return None
        except Exception as e:
            logger.error(f"Failed to get comment {cid}: {e}")
            return None
    
    async def get_subplebbit_posts(self, address: str, sort: str = "hot", limit: int = 50) -> List[PlebbitPost]:
        """Get posts from a subplebbit"""
        try:
            # Get the first page of posts
            result = await self._api_call(f"/subplebbit/{address}/posts/{sort}?limit={limit}")
            
            posts = []
            if result and "comments" in result:
                for post_data in result["comments"]:
                    post = PlebbitPost.from_plebbit_json(post_data)
                    posts.append(post)
            
            # Cache posts
            self.posts_cache[address] = posts
            return posts
        except Exception as e:
            logger.error(f"Failed to get posts from {address}: {e}")
            return []
    
    async def list_default_subplebbits(self) -> List[PlebbitSub]:
        """Get default subplebbits (like plebbit.eth/p/all)"""
        try:
            result = await self._api_call("/defaults")
            
            subs = []
            if result and "multisubAddresses" in result:
                for multisub_name, address in result["multisubAddresses"].items():
                    sub = await self.get_subplebbit(address)
                    if sub:
                        subs.append(sub)
            
            return subs
        except Exception as e:
            logger.error(f"Failed to list default subplebbits: {e}")
            return []
    
    async def get_cached_posts(self, sub_address: str) -> List[PlebbitPost]:
        """Get cached posts for a subplebbit"""
        return self.posts_cache.get(sub_address, [])
    
    async def health_check(self) -> Dict[str, Any]:
        """Check bridge and Plebbit daemon health"""
        try:
            # Test API connection
            await self._api_call("/")
            
            return {
                "status": "healthy",
                "api_base": self.api_base,
                "cached_subplebbits": len(self.posts_cache),
                "total_cached_posts": sum(len(posts) for posts in self.posts_cache.values())
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

class BridgeServer:
    """HTTP server exposing P2P content as REST API"""
    
    def __init__(self, bridge: PlebbitBridge, host: str = "0.0.0.0", port: int = 8001):
        self.bridge = bridge
        self.host = host
        self.port = port
    
    async def start(self):
        """Start the bridge HTTP server"""
        from fastapi import FastAPI, HTTPException
        import uvicorn
        
        app = FastAPI(title="Plebx P2P Bridge", version="0.2.0")
        
        @app.get("/health")
        async def health():
            return await self.bridge.health_check()
        
        @app.get("/subs")
        async def list_subs():
            """List default subplebbits"""
            subs = await self.bridge.list_default_subplebbits()
            return [asdict(sub) for sub in subs]
        
        @app.get("/subs/{address}")
        async def get_sub(address: str):
            """Get specific subplebbit info"""
            sub = await self.bridge.get_subplebbit(address)
            if not sub:
                raise HTTPException(status_code=404, detail="Subplebbit not found")
            return asdict(sub)
        
        @app.get("/subs/{address}/posts")
        async def get_sub_posts(address: str, sort: str = "hot", limit: int = 50):
            """Get posts from a subplebbit"""
            posts = await self.bridge.get_subplebbit_posts(address, sort, limit)
            return [asdict(post) for post in posts]
        
        @app.get("/posts/{cid}")
        async def get_post(cid: str):
            """Get a specific post/comment"""
            post = await self.bridge.get_comment(cid)
            if not post:
                raise HTTPException(status_code=404, detail="Post not found")
            return asdict(post)
        
        config = uvicorn.Config(app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        await server.serve()

def check_plebbit_daemon() -> bool:
    """Check if Plebbit daemon is running"""
    try:
        # Try to connect to default API URL
        response = requests.get("http://localhost:9138/", timeout=5)
        return response.status_code == 200
    except:
        return False

async def main():
    """Main entry point"""
    logger.info("Starting Plebx P2P Bridge Service...")
    
    # Check if Plebbit daemon is running
    if not check_plebbit_daemon():
        logger.error("Plebbit daemon not running.")
        logger.info("Install bitsocial-cli: npm install -g bitsocialhq/bitsocial-cli")
        logger.info("Start daemon: bitsocial daemon")
        return
    
    # Initialize bridge
    bridge = PlebbitBridge()
    
    # Test connection
    health = await bridge.health_check()
    if health.get("status") != "healthy":
        logger.error(f"Failed to connect to Plebbit daemon: {health}")
        return
    
    logger.info("✓ Connected to Plebbit daemon")
    
    # Start HTTP server
    server = BridgeServer(bridge)
    try:
        logger.info(f"Starting bridge server on {server.host}:{server.port}")
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main())