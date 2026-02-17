# Port Sharing Guide for Google Antigravity

When accessing the Plebx application remotely via Google Antigravity port sharing, you need to share the following ports:

## Required Ports

### Frontend
- **Port 3000** - Web UI (React frontend)
  - Access the application at: `http://localhost:3000`

### Backend API
- **Port 8010** - Main API server (FastAPI)
  - Handles feed requests, user management, and post operations
  - Container internal port 8000 is mapped to host port 8010

### P2P Bridge (Optional - for live Plebbit data)
- **Port 8001** - P2P Bridge service
  - Provides health checks and direct bridge access
  - Currently running as a standalone Python script

### Bitsocial Daemon
- **Port 9138** - Bitsocial RPC WebSocket + Web UI
  - Required for P2P bridge to connect to Plebbit network
  - The bridge connects to `ws://localhost:9138/plebx`

### Supporting Services (Internal - not required for remote access)
- Port 6333 - Qdrant vector database
- Port 6379 - Redis cache

## Port Sharing Setup

To share these ports with Google Antigravity:

1. Share port **3000** for the web interface
2. Share port **8010** for the API backend
3. Share port **9138** if you want to access the Bitsocial Web UI
4. Optionally share port **8001** for direct bridge health checks

## Current Configuration

```yaml
# docker-compose.yml port mappings:
web:      3000:80     # Frontend
api:      8010:8000   # Backend API
bitsocial: 9138:9138  # Daemon (if enabled)
```

## Troubleshooting

### 401 Unauthorized Error
- **Cause**: Frontend trying to connect to wrong port
- **Fix**: Ensure `API_BASE` in `frontend/src/Feed.jsx` is set to `http://localhost:8010`

### Bridge Status Unknown
- **Cause**: Bridge service not exposing health endpoint
- **Fix**: Ensure bridge is running and accessible on port 8001

### Connection Refused
- **Cause**: Service not running or port not shared
- **Fix**: 
  1. Check service is running: `docker-compose ps`
  2. Verify port is shared in Antigravity settings
  3. Check firewall rules if applicable
