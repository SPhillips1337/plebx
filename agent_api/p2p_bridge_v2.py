import asyncio
import json
import logging
import websockets
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class PlebbitBridge:
    """Connects to Bitsocial daemon via WebSocket RPC"""
    def __init__(self, api_base: str = None):
        self.api_base = api_base or os.environ.get("BITSOCIAL_DAEMON_URL", "ws://localhost:9138/plebx")
        self.rpc_url = self.api_base.strip('/')
        self.websocket = None
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._initial_subs_future = None
        logger.info(f"PlebbitBridge initialized with RPC URL: {self.rpc_url}")

    async def connect(self):
        if self.websocket:
            return True
        try:
            self.websocket = await websockets.connect(self.rpc_url)
            logger.info("Successfully connected to WebSocket RPC")
            asyncio.create_task(self._listen_loop())
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

    async def _listen_loop(self):
        """Continuously listen for incoming messages and route them"""
        try:
            while True:
                response = await self.websocket.recv()
                data = json.loads(response)
                
                # 1. Handle regular RPC responses
                msg_id = data.get("id")
                if msg_id and msg_id in self._response_futures:
                    self._response_futures[msg_id].set_result(data)
                    del self._response_futures[msg_id]
                    continue
                
                # 2. Handle notifications (like subplebbitsNotification)
                method = data.get("method")
                if method == "subplebbitsNotification":
                    await self._handle_notification(data)
                elif not msg_id:
                    logger.debug(f"Received non-RPC message: {data}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.websocket = None
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")

    async def _handle_notification(self, data: Dict[str, Any]):
        """Handle incoming notifications from the daemon"""
        params = data.get("params", {})
        if data.get("method") == "subplebbitsNotification":
            result = params.get("result", [])
            logger.info(f"Subplebbits notification received: {len(result)} subs")
            if self._initial_subs_future and not self._initial_subs_future.done():
                self._initial_subs_future.set_result(result)

    async def _rpc_call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        """Call an RPC method and wait for its specific response ID"""
        if not self.websocket:
            connected = await self.connect()
            if not connected:
                raise Exception("Not connected to Plebbit RPC")
        
        msg_id = f"{method}_{datetime.now().timestamp()}_{os.urandom(4).hex()}"
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else [],
            "id": msg_id
        }
        
        future = asyncio.get_event_loop().create_future()
        self._response_futures[msg_id] = future
        
        await self.websocket.send(json.dumps(request))
        
        try:
            response_data = await asyncio.wait_for(future, timeout=10.0)
            if "error" in response_data:
                raise Exception(f"RPC Error: {response_data['error']}")
            return response_data.get("result")
        except asyncio.TimeoutError:
            if msg_id in self._response_futures:
                del self._response_futures[msg_id]
            raise Exception(f"RPC Timeout calling {method}")

    async def list_subplebbits(self):
        """Retrieve subscribed subplebbits mapping both immediate and notify responses"""
        self._initial_subs_future = asyncio.get_event_loop().create_future()
        
        try:
            # subplebbitsSubscribe returns { subscription: ID, result: [...] }
            response = await self._rpc_call("subplebbitsSubscribe")
            
            # If the immediate response has the result, use it
            if response and isinstance(response, dict) and "result" in response:
                return response["result"]
            
            # If we don't have it yet, wait for the notification
            logger.info("Immediate response didn't contain 'result', waiting for subplebbitsNotification...")
            return await asyncio.wait_for(self._initial_subs_future, timeout=5.0)
        except Exception as e:
            logger.error(f"Failed to list subplebbits: {e}")
            return []
        finally:
            self._initial_subs_future = None

    async def get_subplebbit_posts(self, subAddress: str, cid: str = "", limit: int = 100):
        """Fetch posts for a subplebbit using verified Zod schema format"""
        params = [{
            "subplebbitAddress": subAddress,
            "cid": cid,
            "type": "posts",
            "pageMaxSize": limit
        }]
        return await self._rpc_call("getSubplebbitPage", params)

    def normalize_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize bridge post format to common Plebx format"""
        return {
            "id": post.get("cid", "unknown"),
            "author_id": post.get("author", "unknown"),
            "content": post.get("content", ""),
            "created_at": post.get("timestamp", datetime.now().isoformat()),
            "score": post.get("votesCount", 0),
            "raw": post
        }

    async def health_check(self):
        try:
            if not self.websocket:
                await self.connect()
            return {"status": "connected", "url": self.rpc_url}
        except Exception as e:
            return {"status": "error", "error": str(e)}