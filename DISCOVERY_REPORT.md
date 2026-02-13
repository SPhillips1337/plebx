# PlebX Discovery Report - 5chan/Plebbit Analysis

## Executive Summary

5chan is a **decentralized imageboard client** built on the **Bitsocial protocol** (which appears to be an evolution of Plebbit). It provides a 4chan-like interface but with completely decentralized board ownership and P2P architecture.

## Key Architecture Insights

### 1. **Decentralized P2P Architecture**
- No central servers - each board runs its own P2P node
- Users connect directly to board nodes via Bitsocial protocol
- Content stored purely peer-to-peer, not in centralized databases
- Board owners run `bitsocial-cli` nodes that serve content

### 2. **Data Access Patterns**
```
Current 5chan approach:
- Direct P2P connections to Bitsocial nodes
- No centralized API or database
- Content accessed via community addresses (IPNS keys/crypto addresses)
- Real-time updates via P2P pubsub

Implications for PlebX:
- Read-only ingestion needs P2P node connectivity
- Cannot rely on simple HTTP APIs
- Need to run Bitsocial nodes or connect to existing ones
```

### 3. **Content Structure**
- **Posts/Comments**: Threaded discussions similar to 4chan
- **Media**: Image uploads with challenge-based spam prevention
- **Boards/Communities**: Decentralized, each owned by different operators
- **Addresses**: IPNS keys (12Koo...) or crypto addresses (domain.eth)

### 4. **Technology Stack**
- **Frontend**: React/TypeScript with Vite
- **P2P**: Bitsocial protocol (Plebbit evolution)
- **Desktop**: Electron with embedded P2P node
- **Mobile**: Capacitor with Android support
- **Real-time**: P2P pubsub (no WebSocket servers)

## Ingestion Strategy Analysis

### Recommended Approach: **Hybrid P2P Bridge**
```
PlebX Bridge Node
├── Bitsocial CLI node (P2P client)
├── Adapter layer (converts P2P events -> REST API)
├── Cache layer (Redis for real-time updates)
└── Storage layer (Postgres for ranked feed)

Benefits:
✓ Preserves P2P nature of source
✓ Enables read-only aggregation
✓ Supports ranking algorithms
✓ Decouples frontend from P2P complexity
```

### Technical Implementation Options

#### Option A: Embedded Bridge (Recommended)
- Run Bitsocial CLI nodes as part of PlebX infrastructure
- Connect to popular/high-quality boards automatically
- Cache posts/comments in local Postgres for ranking
- Subscribe to real-time updates via P2P pubsub

#### Option B: External Bridge
- Require users to run their own Bitsocial nodes
- PlebX connects to user's local node via RPC
- More decentralized but complex user experience

## Data Model Mapping

### Bitsocial → PlebX Canonical Schema
```yaml
User:
  id: bitsocial_address
  username: bitsocial_address # May need display names
  display_name: "Anonymous #1234" # Generated
  avatar_url: null # Bitsocial doesn't have avatars
  external_bitsocial_id: bitsocial_address

Post:
  id: cid
  author_id: bitsocial_address
  content: text_content
  created_at: timestamp
  attachments: [media_files]
  reply_to: parent_cid_or_null
  external_bitsocial_cid: cid
  board_address: community_address

Thread:
  thread_id: root_post_cid
  root_post_id: root_post_cid
  participants: [unique_authors]
  last_activity_at: latest_comment_timestamp
  board_address: community_address
```

## Integration Challenges

### 1. **Real-time Updates**
- Challenge: P2P pubsub vs HTTP/WebSocket
- Solution: Bridge node translates P2P events to WebSocket

### 2. **Content Discovery**
- Challenge: No centralized board directory
- Solution: Maintain curated list of quality boards, or implement board voting

### 3. **Identity Bridge**
- Challenge: Bitsocial addresses vs social profiles
- Solution: Map Bitsocial addresses to PlebX user profiles with enhanced features

### 4. **Media Handling**
- Challenge: P2P content addressing vs traditional URLs
- Solution: Proxy P2P media through PlebX CDN for better performance

## Development Impact

### Phase 1 MVP Adjustments
```
Original Plan:
- HTTP API adapter to Plebbit DB
✓ Adjusted: P2P bridge via Bitsocial CLI

Modified MVP:
1. Bitsocial bridge service
2. Content normalization and caching
3. Basic ranking on cached content
4. React frontend with WebSocket updates
```

### New Components Needed
1. **Bitsocial Bridge Service** - Connects to P2P nodes
2. **Content Cache** - Postgres for ranking queries  
3. **Real-time Translator** - P2P pubsub → WebSocket
4. **Media Proxy** - P2P content → CDN-friendly URLs

## Risk Assessment

### Low Risk
- Content structure is well-understood
- Bitsocial CLI provides programmatic access
- React frontend expertise exists in codebase

### Medium Risk  
- P2P node reliability (depends on board uptime)
- Real-time event translation complexity
- Discovery of quality boards

### High Risk
- Scaling P2P connections (many boards = many connections)
- Legal/regulatory considerations for P2P content
- Performance vs native P2P clients

## Recommendations

### 1. **Proceed with Hybrid P2P Bridge**
- Start with embedded Bitsocial nodes
- Focus on high-quality, reliable boards
- Implement robust fallback handling

### 2. **Adjust Success Criteria**
- Add "P2P bridge uptime" metric
- Include "board discovery" success measure
- Consider "content freshness" vs P2P native

### 3. **Development Priority**
1. P2P bridge prototype (connect to 1-2 boards)
2. Content normalization and caching
3. Basic ranking on cached data
4. Frontend integration with real-time updates

## Next Steps

1. **Prototype P2P Bridge** - Test Bitsocial CLI integration
2. **Board Selection** - Identify initial boards to bridge
3. **Content Schema Validation** - Test with real Bitsocial data
4. **Performance Testing** - Measure P2P → REST translation overhead

---

**Conclusion**: 5chan's P2P architecture requires a bridge approach rather than direct API access. The technical complexity is manageable but requires P2P expertise. The decentralized nature aligns well with PlebX's goals while enabling the desired social overlay features.