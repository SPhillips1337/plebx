#!/usr/bin/env python3
"""
Simplified P2P Bridge Service - Manual daemon mode
Expects plebbit/bitsocial daemon to be running manually
"""
import asyncio
import logging
import requests
import os
from p2p_bridge_v2 import PlebbitBridge, BridgeServer

BITSOCIAL_DAEMON_URL = os.environ.get("BITSOCIAL_DAEMON_URL", "http://localhost:9138/")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_daemon_status() -> bool:
    """Check if daemon is running"""
    try:
        response = requests.get(BITSOCIAL_DAEMON_URL, timeout=5)
        return response.status_code == 200
    except:
        return False

async def main():
    """Main entry point"""
    logger.info("Starting simplified Plebx P2P Bridge Service...")
    
    # Check daemon status
    if not await check_daemon_status():
        logger.error(f"❌ Plebbit daemon not running on {BITSOCIAL_DAEMON_URL}")
        logger.info("📋 Manual setup required:")
        logger.info("   1. Install: npm install -g bitsocialhq/bitsocial-cli")
        logger.info("   2. Start: bitsocial daemon")
        logger.info("   3. Retry this service")
        return
    
    logger.info("✅ Plebbit daemon detected!")
    
    # Initialize bridge
    bridge = PlebbitBridge()
    
    # Test bridge connection
    try:
        health = await bridge.health_check()
        logger.info(f"✅ Bridge health: {health}")
    except Exception as e:
        logger.error(f"❌ Bridge health check failed: {e}")
        return
    
    # Start bridge server
    server = BridgeServer(bridge)
    try:
        logger.info("🌉 Starting bridge server on http://0.0.0.0:8001")
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main())