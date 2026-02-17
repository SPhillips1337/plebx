# Bridge Connectivity Handover & Learnings

## Current Status
Established WebSocket connectivity between the bridge and the Bitsocial daemon. However, RPC calls are currently returning `{"code":-32601,"message":"Method not found"}` despite identifying correct method names from the source code.

## Key Learnings

### 1. Protocol & Authentication
- **Protocol**: The Bitsocial daemon uses **WebSocket RPC**, not HTTP.
- **Port**: `9138` (default).
- **Authentication**: The path suffix (e.g., `/plebx/`) is the `PLEBBIT_RPC_AUTH_KEY`.
- **Remote Host**: When connecting from a container to the host, use `host.docker.internal` (Windows/Mac) or the host's actual IP on Linux.

### 2. Service Mounting
- The daemon binds to `http://0.0.0.0:9138`.
- The Express server (`daemon-server.ts`) serves WebUIs but does NOT handle the RPC calls.
- The WebSocket RPC server is attached directly to the same HTTP port and handled by `rpc-websockets`.

### 3. Namespace & Routing
- Methods are registered in two namespaces:
  1. Default: `/`
  2. Authenticated: `/${rpcAuthKey}` (e.g., `/plebx`)
- Identified methods (from `plebbit-js/src/rpc/src/index.ts`):
  - `getSubplebbitPage`
  - `getCommentPage`
  - `getVersion`
  - `subplebbitsSubscribe`
  - `publishComment`

## Blockers
- **"Method not found"**: Even when using the correct URL (`ws://localhost:9138/plebx/`) and correct method names (e.g., `getSubplebbitPage`), the server rejects the calls.
- **Hypothesis**: The `@plebbit/plebbit-js` RPC layer might require a specific frame format or a custom handshake that isn't satisfied by raw JSON-RPC over `websockets` in Python.

## Successes
- Switched the bridge from `requests` (HTTP) to `websockets` (WS).
- Correctly routing through the auth key path.
- Verified that the daemon is listening and accepting connections.

## Next Steps for Tomorrow
1. **Intercept Traffic**: Use a tool like `tshark` or `tcpdump` to intercept the communication between `bitsocial-cli` and the daemon to see the exact payload structure.
2. **Library Investigation**: Review `rpc-websockets` (Node.js) vs Python `websockets` compatibility.
3. **Use the SDK**: If raw JSON-RPC fails, consider creating a small Node.js sidecar or using a Python library that perfectly mimics the expected RPC behavior.
