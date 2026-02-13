# Plebx P2P Bridge Service

## Overview

The P2P Bridge is the core component that connects PlebX to the Plebbit/Bitsocial network. It translates P2P content into a REST API that the PlebX frontend can consume.

## Architecture

```
Plebbit P2P Network → Plebbit Daemon → P2P Bridge → REST API → PlebX Frontend
```

## Components

### 1. P2P Bridge (`p2p_bridge_v2.py`)
- **Connection**: HTTP API to Plebbit daemon (localhost:9138)
- **Translation**: Converts Plebbit data structures to canonical PlebX format
- **Caching**: In-memory cache for subplebbits and posts
- **Health Monitoring**: Built-in health checks

### 2. Bridge Server (`BridgeServer` class)
- **FastAPI**: REST API server on port 8001
- **Endpoints**: 
  - `GET /health` - Bridge health status
  - `GET /subs` - List default subplebbits
  - `GET /subs/{address}` - Get subplebbit info
  - `GET /subs/{address}/posts` - Get posts from subplebbit
  - `GET /posts/{cid}` - Get specific post/comment

## Data Models

### PlebbitPost
Canonical representation of posts/comments from Plebbit network:
- Core fields: `cid`, `author`, `subplebbit_address`, `timestamp`, `content`
- Media: `link`, `thumbnail_url`, `link_width/height`
- Metadata: `flair`, `spoiler`, `pinned`, `reply_count`, `upvote_count`

### PlebbitSub  
Board/community information:
- Identity: `address`, `title`, `description`
- Configuration: `features`, `rules`, `flairs`, `suggested`
- State: `last_post_cid`, `updated_at`

## Setup

### Prerequisites
1. **Install Plebbit CLI**:
   ```bash
   npm install -g @plebbit/plebbit-cli
   ```

2. **Start Plebbit Daemon**:
   ```bash
   plebbit daemon
   ```

3. **Install Python Dependencies**:
   ```bash
   pip install -r agent_api/requirements.txt
   ```

### Running the Bridge

#### Development
```bash
cd agent_api
python p2p_bridge_v2.py
```

#### Testing
```bash
python test_bridge.py
```

## API Endpoints

### Health Check
```bash
GET http://localhost:8001/health
```

Response:
```json
{
  "status": "healthy",
  "api_base": "http://localhost:9138",
  "cached_subplebbits": 5,
  "total_cached_posts": 127
}
```

### List Subplebbits
```bash
GET http://localhost:8001/subs
```

### Get Subplebbit
```bash
GET http://localhost:8001/subs/pleblore.eth
```

### Get Posts
```bash
GET http://localhost:8001/subs/pleblore.eth/posts?sort=hot&limit=20
```

### Get Post
```bash
GET http://localhost:8001/posts/QmXxx...
```

## Integration with PlebX

### Adapter Integration
The bridge replaces the placeholder adapter in `adapter.py`:

```python
# In agent_api/adapter.py
from p2p_bridge_v2 import PlebbitBridge

class Adapter:
    def __init__(self):
        self.bridge = PlebbitBridge()
    
    async def fetch_recent_posts(self, limit: int = 100):
        # Get from popular subplebbits
        subs = await self.bridge.list_default_subplebbits()
        all_posts = []
        for sub in subs[:5]:  # Top 5 subplebbits
            posts = await self.bridge.get_subplebbit_posts(sub.address, limit=limit//5)
            all_posts.extend(posts)
        
        return [self.normalize_post(post) for post in all_posts[:limit]]
```

### Frontend Integration
Update frontend to use bridge endpoints:

```javascript
// In frontend/src/App.jsx
const API_BASE = 'http://localhost:8001';

// Fetch feed
async function fetchFeed() {
  const response = await fetch(`${API_BASE}/subs/pleblore.eth/posts?sort=hot&limit=50`);
  return await response.json();
}
```

## Next Steps

1. **Real-time Updates**: Implement WebSocket for live post updates
2. **Authentication**: Connect Plebbit author addresses to PlebX profiles  
3. **Ranking Integration**: Feed posts into ranking service
4. **Media Handling**: Proxy and optimize images/media
5. **Error Handling**: Robust retry logic for P2P network issues

## Troubleshooting

### Common Issues

**"Plebbit daemon not running"**
- Install: `npm install -g @plebbit/plebbit-cli`
- Start: `plebbit daemon`
- Check: `curl http://localhost:9138/`

**"No subplebbits found"**
- Daemon needs time to sync with network
- Try specific subplebbit: `GET /subs/pleblore.eth`

**"Connection refused"**
- Check port 9138 is available
- Verify daemon is running with correct config

## Monitoring

The bridge includes built-in health monitoring:
- Connection status to Plebbit daemon
- Cache statistics
- Error rates and types

Use with monitoring tools:
```bash
# Health check endpoint
watch -n 5 curl http://localhost:8001/health

# Log monitoring
tail -f logs/bridge.log
```