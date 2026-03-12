# PlebX Usage Guide

Complete guide for developers using and extending PlebX social overlay.

## 🚀 Quick Start

### 1. Prerequisites

#### Required Software
- **Node.js 22+** (for Plebbit CLI)
- **Python 3.11+** (for backend services)
- **Docker & Docker Compose** (for development stack)
- **Git** (for version control)

#### Environment Setup
```bash
# Clone the repository
git clone https://github.com/your-org/plebx.git
cd plebx

# Copy environment file
cp .env.example .env

# Edit with your configuration
nano .env
```

### 2. Core Services Setup

#### A. Plebbit P2P Network
```bash
# Install Plebbit CLI globally
npm install -g @plebbit/plebbit-cli

# Start the daemon (required for P2P bridge)
#plebbit daemon
bitsocial daemon
# Verify daemon is running
curl http://localhost:9138/
```

#### B. Development Stack (Docker)
```bash
# Start all services (Postgres, Redis, Qdrant, API)
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f api
```

#### C. P2P Bridge Only (Development)
```bash
# Install Python dependencies
cd agent_api
pip install -r requirements.txt

# Start bridge service (port 8001)
python p2p_bridge_v2.py

# Test bridge
python test_bridge.py
```

#### D. Frontend Development
```bash
# Install frontend dependencies
cd frontend
npm install

# Start development server
npm run dev

# Access at http://localhost:3000
```

## 📡 API Usage

### Base URLs
```
P2P Bridge API:  http://localhost:8001
Main API:        http://localhost:8000
Frontend:         http://localhost:3000
```

### P2P Bridge Endpoints

#### Health & Status
```bash
GET /health
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

#### Subplebbit Discovery
```bash
# List default subplebbits (plebbit.eth/p/all)
GET /subs

# Get specific subplebbit info
GET /subs/pleblore.eth

# Response
{
  "address": "pleblore.eth",
  "title": "Plebbit Lore",
  "description": "Discussions about plebbit history",
  "created_at": 1640995200,
  "rules": ["No spam", "Be civil"],
  "last_post_cid": "QmXxx..."
}
```

#### Content Retrieval
```bash
# Get posts from subplebbit
GET /subs/pleblore.eth/posts?sort=hot&limit=50

# Available sort types: hot, new, topAll, topDay, topWeek, topMonth

# Get specific post/thread
GET /posts/QmXxx...

# Response
{
  "cid": "QmXxx...",
  "author": {
    "address": "12D3KooW...",
    "shortAddress": "12D3KooW..."
  },
  "subplebbit_address": "pleblore.eth",
  "timestamp": 1640995200,
  "content": "This is a post about plebbit...",
  "title": "Welcome to Plebbit",
  "depth": 0,
  "reply_count": 5,
  "upvote_count": 12,
  "downvote_count": 1
}
```

### Main API Endpoints

#### Feed Generation
```bash
# Get ranked feed
GET /feed?user_id=xxx&limit=50&sort=hot

# Create post (optional write-back)
POST /post
{
  "content": "Hello PlebX!",
  "subplebbit_address": "memes.eth",
  "title": "My first post"
}
```

#### User Management
```bash
# Get user profile
GET /user/12D3KooW...

# Update profile
PUT /user/12D3KooW...
{
  "display_name": "PlebX User",
  "bio": "Active on Plebbit and PlebX",
  "avatar_url": "https://example.com/avatar.jpg"
}
```

## 🎨 Frontend Development

### Component Architecture
```javascript
// Main application structure
src/
├── App.jsx              # Main router and layout
├── components/
│   ├── Feed.jsx       # Timeline feed (posts)
│   ├── ThreadView.jsx # Post with comments
│   ├── Profile.jsx    # User profiles
│   ├── Composer.jsx   # Post creation
│   └── Navigation.jsx  # Site navigation
├── hooks/
│   ├── useFeed.js     # Feed data fetching
│   ├── useAuth.js     # Authentication
│   └── useRealtime.js # WebSocket updates
└── services/
    └── api.js         # API client
```

### Data Fetching Patterns
```javascript
// Hook for fetching feed
import { useState, useEffect } from 'react';

export function useFeed(options = {}) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchFeed() {
      try {
        const response = await fetch(`${API_BASE}/feed?${new URLSearchParams(options)}`);
        const data = await response.json();
        setPosts(data.posts || data);
      } catch (error) {
        console.error('Failed to fetch feed:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchFeed();
  }, [options.sort, options.limit, options.user_id]);

  return { posts, loading, refetch: fetchFeed };
}

// Usage in component
function Feed() {
  const { posts, loading, refetch } = useFeed({ sort: 'hot', limit: 50 });

  if (loading) return <LoadingSpinner />;
  
  return (
    <div className="feed">
      {posts.map(post => <Post key={post.cid} post={post} />)}
    </div>
  );
}
```

### Real-time Updates
```javascript
// WebSocket connection for live updates
export function useRealtime(callbacks) {
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8001/ws');
    
    ws.onopen = () => {
      console.log('Connected to real-time updates');
      ws.send(JSON.stringify({ type: 'subscribe', channels: ['posts', 'comments'] }));
    };
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      callbacks[message.type]?.(message.data);
    };
    
    return () => ws.close();
  }, [callbacks]);
}

// Usage
function Feed() {
  const [posts, setPosts] = useState([]);
  
  useRealtime({
    'new_post': (post) => setPosts(prev => [post, ...prev]),
    'updated_post': (post) => setPosts(prev => 
      prev.map(p => p.cid === post.cid ? post : p)
    )
  });
}
```

## 🔧 Configuration

### Environment Variables
```bash
# .env file
# Plebbit Configuration
PLEBBIT_RPC_URL=http://localhost:9138

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/plebx
REDIS_URL=redis://localhost:6379

# Object Storage
S3_BUCKET=plebx-media
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Optional Features
ENABLE_WRITE_BACK=false
FEATURE_AGENT_MODE=true
```

### Docker Configuration
```yaml
# docker-compose.yml override
version: '3.8'
services:
  api:
    build: ./agent_api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - PLEBBIT_RPC_URL=${PLEBBIT_RPC_URL}
    depends_on:
      - postgres
      - redis
      - qdrant

  bridge:
    build: ./agent_api
    command: python p2p_bridge_v2.py
    ports:
      - "8001:8001"
    environment:
      - PLEBBIT_RPC_URL=${PLEBBIT_RPC_URL}

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
```

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
cd agent_api
pytest

# Run specific test file
pytest tests/test_bridge.py

# Run with coverage
pytest --cov=. tests/

# Test P2P bridge specifically
python test_bridge.py
```

### Frontend Tests
```bash
# Install test dependencies
cd frontend
npm install

# Run unit tests
npm test

# Run integration tests
npm run test:integration

# End-to-end tests
npm run test:e2e
```

### Load Testing
```bash
# Test API performance
cd tests
python load_test_api.py --concurrent=100 --duration=60s

# Test P2P bridge load
python load_test_bridge.py --requests=1000
```

## 📊 Monitoring & Debugging

### Health Checks
```bash
# Check all services
curl http://localhost:8000/health  # Main API
curl http://localhost:8001/health  # P2P Bridge
curl http://localhost:3000           # Frontend

# Docker services
docker compose ps
docker compose logs api
```

### Log Analysis
```bash
# API logs
tail -f logs/api.log

# Bridge logs
tail -f logs/bridge.log

# Docker logs
docker compose logs -f api bridge postgres redis qdrant
```

### Database Queries
```sql
-- Top posts in last hour
SELECT * FROM posts 
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY upvote_count DESC;

-- Active users
SELECT DISTINCT author_address 
FROM posts 
WHERE created_at > NOW() - INTERVAL '24 hours';

-- Subplebbit activity
SELECT subplebbit_address, COUNT(*) as post_count
FROM posts 
GROUP BY subplebbit_address
ORDER BY post_count DESC
LIMIT 20;
```

## 🚨 Troubleshooting

### Common Issues

#### "Plebbit daemon not running"
```bash
# Install CLI
npm install -g @plebbit/plebbit-cli

# Start daemon
plebbit daemon

# Verify
curl http://localhost:9138/
```

#### "No posts in bridge"
```bash
# Check daemon status
curl http://localhost:8001/health

# Clear cache and restart
curl -X POST http://localhost:8001/clear-cache
```

#### "Database connection errors"
```bash
# Check Postgres
docker compose ps postgres
docker compose logs postgres

# Reset database
docker compose down -v
docker compose up -d
```

#### "Frontend build errors"
```bash
# Clear dependencies
rm -rf node_modules package-lock.json
npm install

# Check environment variables
echo $REACT_APP_API_URL
```

## 🔐 Security Considerations

### Development
- Never commit `.env` files to version control
- Use read-only database credentials for development
- Enable security headers in production

### Production
- Use HTTPS for all API endpoints
- Implement rate limiting
- Sanitize all user inputs
- Monitor for suspicious activity

## 📈 Performance Optimization

### Database Indexes
```sql
-- Essential indexes for performance
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX idx_posts_author ON posts(author_address);
CREATE INDEX idx_posts_subplebbit ON posts(subplebbit_address);
CREATE INDEX idx_posts_upvotes ON posts(upvote_count DESC);
```

### Caching Strategy
```bash
# Redis cache warming
curl -X POST http://localhost:8001/warm-cache

# Clear specific cache
curl -X DELETE http://localhost:8001/cache/subs/memes.eth
```

## 🔌 API Rate Limits

### Default Limits
- **Feed requests**: 100/minute per IP
- **Post creation**: 10/minute per user  
- **Profile updates**: 5/minute per user
- **Media uploads**: 20/minute per user

### Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1640995200
```

## 📝 Development Workflow

### Daily Development
```bash
# Morning setup
git checkout -b feature/new-feature
docker compose up -d
cd agent_api && python p2p_bridge_v2.py &
cd frontend && npm run dev &

# Work session
# Make changes
git add .
git commit -m "Add feature X"
git push origin feature/new-feature

# End of day
docker compose down
```

### Release Process
```bash
# Tag and deploy
git tag v0.1.0
git push origin v0.1.0

# Build for production
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

---

For additional help, see:
- [DISCOVERY_REPORT.md](DISCOVERY_REPORT.md) - Technical analysis
- [BRIDGE_README.md](BRIDGE_README.md) - Bridge details  
- [AGENTS.md](AGENTS.md) - AI development guidelines

Or check the project repository issues and discussions.