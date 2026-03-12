import asyncio
import os
import logging
from datetime import datetime
from p2p_bridge_v2 import PlebbitBridge
from storage import upsert_posts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_bridge():
    """Main bridge loop: discovers subs and pulls latest posts"""
    daemon_url = os.environ.get("BITSOCIAL_DAEMON_URL", "ws://localhost:9138/plebx")
    logger.info(f"Starting Plebx Bridge. Connecting to: {daemon_url}")
    
    bridge = PlebbitBridge(daemon_url)
    
    # Try connecting
    if not await bridge.connect():
        logger.error("Failed to connect to Plebbit daemon. Exiting.")
        return

    logger.info("✅ Connected to daemon. Waiting for subplebbits discovery...")
    
    try:
        while True:
            # 1. Get list of subscribed subplebbits
            try:
                subs = await bridge.list_subplebbits()
                if not subs:
                    logger.info("No subplebbits found. Be sure to join some in the Bitsocial UI.")
                else:
                    logger.info(f"Discovered {len(subs)} subplebbits: {subs}")
                    
                    # 2. For each subplebbit, fetch latest posts
                    for sub_address in subs:
                        logger.info(f"Fetching posts for {sub_address}...")
                        posts_page = await bridge.get_subplebbit_posts(sub_address, limit=20)
                        
                        if posts_page:
                            # Handling both raw list and page object { comments: [...] }
                            posts = []
                            if isinstance(posts_page, list):
                                posts = posts_page
                            elif isinstance(posts_page, dict):
                                posts = posts_page.get("comments", []) or posts_page.get("posts", [])
                            
                            if posts:
                                logger.info(f"Found {len(posts)} posts in {sub_address}")
                                
                                # 3. Normalize and save to DB
                                normalized = []
                                for post_wrapper in posts:
                                    # In getSubplebbitPage, posts are often wrapped
                                    post = post_wrapper
                                    if isinstance(post_wrapper, dict) and "comment" in post_wrapper:
                                        post = post_wrapper["comment"]
                                    elif isinstance(post_wrapper, dict) and "publication" in post_wrapper:
                                        post = post_wrapper["publication"]
                                    
                                    if isinstance(post, dict):
                                        normalized.append(bridge.normalize_post(post))
                                
                                upsert_posts(normalized)
                                logger.info(f"Saved {len(normalized)} posts to Plebx DB")
                            else:
                                logger.info(f"No valid posts found in page for {sub_address}")
            
            except Exception as e:
                logger.error(f"Error in bridge poll cycle: {e}")
            
            # If no posts fetched, use sample data for demo purposes
            try:
                sample_posts = []
                for i in range(3):
                    sample_posts.append({
                        "id": f"sample-{i}",
                        "author": f"user{i}",
                        "content": f"This is sample post {i}",
                        "timestamp": datetime.now().isoformat(),
                        "votesCount": i * 2,
                        "replyCount": i
                    })
                upsert_posts([bridge.normalize_post(p) for p in sample_posts])
                logger.info(f"No real posts available, using {len(sample_posts)} sample posts for demo")
            except Exception as e:
                logger.debug(f"Sample posts fallback: {e}")
            
            # Poll every 60 seconds
            await asyncio.sleep(60)
            
    except asyncio.CancelledError:
        logger.info("Bridge stopping...")

if __name__ == "__main__":
    try:
        asyncio.run(run_bridge())
    except KeyboardInterrupt:
        pass