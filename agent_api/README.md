Agent API

- app.py : minimal FastAPI app (health + /triage placeholder)
- adapter.py : scaffold for ingestion adapters (db/api/ipfs). Implement connectors here.

Usage:
  python3 agent_api/adapter.py

New: simple sqlite persistence is included in `agent_api/storage.py`. On startup the service will create `data/plebx.db`.

You can seed the DB by using the adapter's sample data and the new upsert path in the code (the service will cache adapter results into the DB when `/feed` is called in non-db modes).
