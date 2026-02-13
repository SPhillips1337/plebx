"""
Plebx P2P Bridge Service
Connects to Bitsocial CLI via WebSocket RPC and translates P2P content to REST API
"""
import asyncio
import json
import logging
import websockets
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import subprocess
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BitsocialPost:
    """Canonical post structure from Bitsocial/P2P network"""
    id: str
    author_id: str
    content: str
    created_at: str
    attachments: List[Dict[str, Any]]
    reply_to: Optional[str] = None
    board_address: str = ""
    cid: str = ""
    signature: Optional[str] = None
    
    @classmethod
    def from_plebbit_json(cls, data: Dict[str, Any], board_address: str) -> "BitsocialPost":
        """Create BitsocialPost from plebbit-js JSON response"""
        return cls(
            id=data.get("cid", data.get("id", "")),
            author_id=data.get("author", {}).get("address", ""),
            content=data.get("content", ""),
            created_at=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            attachments=data.get("media", []),
            reply_to=data.get("replyTo", {}).get("cid") if data.get("replyTo") else None,
            board_address=board_address,
            cid=data.get("cid", ""),
            signature=data.get("signature", "")
        )

@dataclass
class BitsocialBoard:
    """Board/community information"""
    address: str
    title: str
    description: str
    created_at: str
    last_activity: Optional[str] = None
    post_count: int = 0

class P2PBridge:
    """Main bridge service connecting PlebX to Bitsocial P2P network"""
    
    def __init__(self, rpc_url: str = "ws://localhost:9138"):
        self.rpc_url = rpc_url
        self.websocket = None
        self.connected_boards = set()
        self.posts_cache = {}  # board_address -> [posts]
        self.subscribed_boards = set()
        
    async def connect(self) -> bool:
        """Connect to Bitsocial RPC WebSocket"""
        try:
            self.websocket = await websockets.connect(self.rpc_url)
            logger.info(f"Connected to Bitsocial RPC at {self.rpc_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Bitsocial RPC: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from RPC"""
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from Bitsocial RPC")
    
    async def _rpc_call(self, method: str, params: Dict[str, Any] = None) -> Any:
        """Make RPC call to Bitsocial daemon"""
        if not self.websocket:
            raise ConnectionError("Not connected to Bitsocial RPC")
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": f"{method}_{datetime.now().timestamp()}"
        }
        
        try:
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if "error" in data:
                raise Exception(f"RPC Error: {data['error']}")
            
            return data.get("result")
        except Exception as e:
            logger.error(f"RPC call failed: {method} - {e}")
            raise
    
    async def list_local_communities(self) -> List[BitsocialBoard]:
        """List communities available in local Bitsocial node"""
        try:
            # Use plebbit-js equivalent of 'bitsocial community list'
            result = await self._rpc_call("plebbit.listSubplebbits", {})
            
            boards = []
            for community_data in result:
                board = BitsocialBoard(
                    address=community_data.get("address", ""),
                    title=community_data.get("title", ""),
                    description=community_data.get("description", ""),
                    created_at=community_data.get("createdAt", ""),
                    last_activity=community_data.get("updatedAt"),
                    post_count=community_data.get("postCount", 0)
                )
                boards.append(board)
            
            return boards
        except Exception as e:
            logger.error(f"Failed to list communities: {e}")
            return []
    
    async def get_community(self, address: str) -> Optional[BitsocialBoard]:
        """Get specific community info"""
        try:
            result = await self._rpc_call("plebbit.getSubplebbit", {"subplebbitAddress": address})
            
            if result:
                return BitsocialBoard(
                    address=result.get("address", address),
                    title=result.get("title", ""),
                    description=result.get("description", ""),
                    created_at=result.get("createdAt", ""),
                    last_activity=result.get("updatedAt"),
                    post_count=result.get("postCount", 0)
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get community {address}: {e}")
            return None
    
    async def get_community_posts(self, address: str, limit: int = 50) -> List[BitsocialPost]:
        """Get posts from a community"""
        try:
            # Get posts from the community
            result = await self._rpc_call("plebbit.getPosts", {
                "subplebbitAddress": address,
                "limit": limit
            })
            
            posts = []
            for post_data in result:
                post = BitsocialPost.from_plebbit_json(post_data, address)
                posts.append(post)
            
            # Cache posts
            self.posts_cache[address] = posts
            return posts
        except Exception as e:
            logger.error(f"Failed to get posts from {address}: {e}")
            return []
    
    async def subscribe_to_community(self, address: str) -> bool:
        """Subscribe to real-time updates from a community"""
        try:
            # Subscribe to pubsub updates
            await self._rpc_call("plebbit.subscribe", {
                "subplebbitAddress": address
            })
            
            self.subscribed_boards.add(address)
            logger.info(f"Subscribed to community updates: {address}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to {address}: {e}")
            return False
    
    async def listen_for_updates(self, callback):
        """Listen for real-time updates from subscribed communities"""
        if not self.websocket:
            raise ConnectionError("Not connected to Bitsocial RPC")
        
        logger.info("Listening for real-time updates...")
        
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                # Handle different types of updates
                if "method" in data and data["method"] == "plebbit.update":
                    await self._handle_update(data["params"], callback)
                    
        except Exception as e:
            logger.error(f"Error listening for updates: {e}")
    
    async def _handle_update(self, update_data: Dict[str, Any], callback):
        """Handle real-time update from Bitsocial"""
        try:
            update_type = update_data.get("type", "")
            board_address = update_data.get("subplebbitAddress", "")
            
            if update_type == "newPost":
                post = BitsocialPost.from_plebbit_json(
                    update_data.get("post", {}), 
                    board_address
                )
                
                # Update cache
                if board_address not in self.posts_cache:
                    self.posts_cache[board_address] = []
                self.posts_cache[board_address].insert(0, post)
                
                # Notify callback
                await callback("new_post", post, board_address)
                
            elif update_type == "updatedPost":
                post = BitsocialPost.from_plebbit_json(
                    update_data.get("post", {}), 
                    board_address
                )
                await callback("updated_post", post, board_address)
                
        except Exception as e:
            logger.error(f"Error handling update: {e}")
    
    async def get_cached_posts(self, board_address: str) -> List[BitsocialPost]:
        """Get cached posts for a board"""
        return self.posts_cache.get(board_address, [])
    
    async def health_check(self) -> Dict[str, Any]:
        """Check bridge and Bitsocial daemon health"""
        try:
            if not self.websocket:
                return {"status": "disconnected", "error": "No WebSocket connection"}
            
            # Test RPC connection
            await self._rpc_call("plebbit.getVersion", {})
            
            return {
                "status": "healthy",
                "connected_boards": len(self.connected_boards),
                "subscribed_boards": len(self.subscribed_boards),
                "cached_posts": sum(len(posts) for posts in self.posts_cache.values())
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

class BridgeServer:
    """HTTP server exposing P2P content as REST API"""
    
    def __init__(self, bridge: P2PBridge, host: str = "0.0.0.0", port: int = 8001):
        self.bridge = bridge
        self.host = host
        self.port = port
    
    async def start(self):
        """Start the bridge HTTP server"""
        from fastapi import FastAPI, HTTPException
        import uvicorn
        
        app = FastAPI(title="Plebx P2P Bridge", version="0.1.0")
        
        @app.get("/health")
        async def health():
            return await self.bridge.health_check()
        
        @app.get("/boards")
        async def list_boards():
            """List available boards"""
            boards = await self.bridge.list_local_communities()
            return [asdict(board) for board in boards]
        
        @app.get("/boards/{address}")
        async def get_board(address: str):
            """Get specific board info"""
            board = await self.bridge.get_community(address)
            if not board:
                raise HTTPException(status_code=404, detail="Board not found")
            return asdict(board)
        
        @app.get("/boards/{address}/posts")
        async def get_board_posts(address: str, limit: int = 50):
            """Get posts from a board"""
            posts = await self.bridge.get_community_posts(address, limit)
            return [asdict(post) for post in posts]
        
        @app.post("/boards/{address}/subscribe")
        async def subscribe_board(address: str):
            """Subscribe to board updates"""
            success = await self.bridge.subscribe_to_community(address)
            return {"subscribed": success}
        
        config = uvicorn.Config(app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        await server.serve()

def check_bitsocial_daemon() -> bool:
    """Check if Bitsocial daemon is running"""
    try:
        # Try to connect to default RPC URL
        import websockets
        async def test_connection():
            try:
                async with websockets.connect("ws://localhost:9138") as ws:
                    return True
            except:
                return False
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_connection())
        loop.close()
        
        return result
    except:
        return False

async def main():
    """Main entry point"""
    logger.info("Starting Plebx P2P Bridge Service...")
    
    # Check if Bitsocial daemon is running
    if not check_bitsocial_daemon():
        logger.error("Bitsocial daemon not running. Please start with: bitsocial daemon")
        logger.info("Install Bitsocial CLI: https://github.com/bitsocialhq/bitsocial-cli")
        return
    
    # Initialize bridge
    bridge = P2PBridge()
    
    # Connect to Bitsocial
    if not await bridge.connect():
        logger.error("Failed to connect to Bitsocial daemon")
        return
    
    # Create update callback
    async def update_callback(update_type: str, post: BitsocialPost, board_address: str):
        logger.info(f"Update: {update_type} - {post.id} from {board_address}")
        # Here you could broadcast updates to WebSocket clients
        # or trigger other processing
    
    # Start listening for updates in background
    update_task = asyncio.create_task(bridge.listen_for_updates(update_callback))
    
    # Start HTTP server
    server = BridgeServer(bridge)
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        update_task.cancel()
        await bridge.disconnect()

if __name__ == "__main__":
    asyncio.run(main())