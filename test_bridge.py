#!/usr/bin/env python3
"""
Test script for Plebx P2P Bridge
"""
import asyncio
import sys
import os

# Add the agent_api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent_api'))

from p2p_bridge_v2 import PlebbitBridge, check_plebbit_daemon

async def test_bridge():
    """Test the bridge connection and basic functionality"""
    print("🔍 Testing Plebx P2P Bridge...")
    
    # Check if Plebbit daemon is running
    print("1. Checking Plebbit daemon...")
    if not check_plebbit_daemon():
        print("❌ Plebbit daemon not running")
        print("   Install: npm install -g @plebbit/plebbit-cli")
        print("   Start: plebbit daemon")
        return False
    
    print("✅ Plebbit daemon is running")
    
    # Initialize bridge
    print("2. Initializing bridge...")
    bridge = PlebbitBridge()
    
    # Test health check
    print("3. Testing health check...")
    health = await bridge.health_check()
    if health.get("status") == "healthy":
        print(f"✅ Bridge healthy: {health}")
    else:
        print(f"❌ Bridge unhealthy: {health}")
        return False
    
    # Test getting default subplebbits
    print("4. Testing subplebbit discovery...")
    try:
        subs = await bridge.list_default_subplebbits()
        print(f"✅ Found {len(subs)} default subplebbits")
        for sub in subs[:3]:  # Show first 3
            print(f"   - {sub.address}: {sub.title or 'No title'}")
    except Exception as e:
        print(f"❌ Failed to list subplebbits: {e}")
        return False
    
    # Test getting posts from a sub
    print("5. Testing post retrieval...")
    if subs:
        try:
            test_sub = subs[0]
            posts = await bridge.get_subplebbit_posts(test_sub.address, limit=3)
            print(f"✅ Retrieved {len(posts)} posts from {test_sub.address}")
            for post in posts:
                author_short = post.get("author", {}).get("shortAddress", "Unknown")
                content_preview = (post.get("content") or "")[:50] + "..." if len(post.get("content") or "") > 50 else (post.get("content") or "No content")
                print(f"   - {post.get('cid', 'No CID')[:12]}... by {author_short}: {content_preview}")
        except Exception as e:
            print(f"❌ Failed to get posts: {e}")
            return False
    
    print("\n🎉 All tests passed! Bridge is ready to use.")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_bridge())
    sys.exit(0 if success else 1)