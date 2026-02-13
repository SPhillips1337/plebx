# PlebX Social Overlay

A middleware overlay that transforms Plebbit (5chan) content into a Twitter/Meet.me-style social experience with ranked feeds, profiles, chat, and image support.

## 🏗️ Architecture

```
Plebitbit P2P Network → P2P Bridge → REST API → Ranking Service → Social UI (React)
```

### Core Components

- **P2P Bridge** (`agent_api/p2p_bridge_v2.py`) - Connects to Plebbit daemon via HTTP API
- **REST API** (`agent_api/app.py`) - FastAPI server with feed and post endpoints  
- **Ranking Service** (`ranking/ranking_service.py`) - Twitter-style algorithm for content scoring
- **Frontend** (`frontend/`) - React SPA with Twitter-like interface
- **Infrastructure** (`docker-compose.yml`) - Postgres, Redis, Qdrant, and API services

## 🚀 Quick Start

### Prerequisites

1. **Install Plebbit CLI**:
   ```bash
   npm install -g @plebbit/plebbit-cli
   ```

2. **Start Plebbit Daemon**:
   ```bash
   plebbit daemon
   ```

3. **Set Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

### Running the Stack

#### Option 1: Development (Docker Compose)
```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f
```

#### Option 2: P2P Bridge Only
```bash
# Start the bridge service
cd agent_api
pip install -r requirements.txt
python p2p_bridge_v2.py
```

## 📁 Project Structure

```
plebx/
├── agent_api/                 # Backend services
│   ├── p2p_bridge_v2.py     # P2P bridge to Plebbit network
│   ├── app.py               # Main FastAPI application
│   ├── adapter.py            # Content normalization layer
│   ├── ranking.py            # Content ranking algorithms
│   └── requirements.txt      # Python dependencies
├── frontend/                  # React social UI
│   ├── src/
│   │   ├── Feed.jsx         # Timeline feed component
│   │   ├── ThreadView.jsx    # Thread view component
│   │   └── Profile.jsx       # User profile component
│   └── package.json
├── ranking/                   # Ranking microservice
│   └── ranking_service.py
├── docker-compose.yml          # Development stack
├── DISCOVERY_REPORT.md        # 5chan/Plebbit analysis
├── BRIDGE_README.md        # P2P bridge documentation
└── README.md                # This file
```

## 🔌 P2P Bridge

The bridge is the core innovation that enables PlebX to read from the decentralized Plebbit network:

### Features
- **Read-only ingestion** - No disruption to existing Plebbit federation
- **Real-time translation** - P2P data to canonical REST API
- **Health monitoring** - Built-in health checks and error handling
- **Caching** - In-memory caching for performance

### API Endpoints
```bash
# Health check
GET http://localhost:8001/health

# List subplebbits (boards)
GET http://localhost:8001/subs

# Get posts from subplebbit
GET http://localhost:8001/subs/{address}/posts?sort=hot&limit=50

# Get specific post
GET http://localhost:8001/posts/{cid}
```

## 🎯 Development Phases

### Phase 0: Discovery ✅
- [x] Audit 5chan codebase and Plebbit protocol
- [x] Design P2P bridge architecture
- [x] Create bridge prototype and documentation

### Phase 1: MVP (Current)
- [ ] Integrate bridge with existing adapter
- [ ] Build React feed component with bridge API
- [ ] Implement basic ranking algorithm
- [ ] Add image upload and NSFW scanning

### Phase 2: Realtime & Messaging
- [ ] WebSocket support for live updates
- [ ] Chat and messaging system
- [ ] Push notifications

### Phase 3: Personalization & Scaling
- [ ] Vector embeddings and search
- [ ] User profiles and follows
- [ ] Advanced ranking algorithms

## 🛠️ Development Workflow

### Local Development
```bash
# Start all services
docker compose up -d

# Frontend development
cd frontend
npm run dev

# API development  
cd agent_api
pip install -r requirements.txt
python app.py
```

### Testing
```bash
# Test P2P bridge
python test_bridge.py

# Run API tests
cd tests
pytest
```

## 📚 Documentation

- **[DISCOVERY_REPORT.md](DISCOVERY_REPORT.md)** - Detailed analysis of 5chan/Plebbit
- **[BRIDGE_README.md](BRIDGE_README.md)** - P2P bridge technical documentation
- **[USAGE.md](USAGE.md)** - Complete usage guide for developers
- **[AGENTS.md](AGENTS.md)** - AI employee development guidelines

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -am "Add amazing feature"`
4. Push branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
