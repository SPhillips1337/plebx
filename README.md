PlebX — Agent scaffold

What I added:
- `agent_spec.yaml` — example agent spec
- `prompts/` — prompt templates
- `tests/` — test placeholders
- `playbooks/incident.md` — incident runbook
- `registry.csv` — agent registry
- `docker-compose.yml` — dev stack (qdrant, redis, api)
- `agent_api/` — minimal FastAPI example and Dockerfile
- `setup.sh` — build & bring up dev stack

Next steps (recommended):
1. Edit `.env` with secrets (OPENAI_API_KEY).
2. Run `./setup.sh` on the server to build and start the stack.
3. Seed RAG index and update `agent_api` with real connectors.

If you want I can now: (1) run `./setup.sh` for you, or (2) keep changes only and not start services. Reply with which.
