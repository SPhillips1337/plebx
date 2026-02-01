PlebX Social Overlay — PLAN

Objective
Build a middleware overlay (PlebX Social) that reads Plebbit-style content (bitsocialhq/5chan), applies a Twitter-style ranking algorithm (twitter/the-algorithm), and provides a Meet.me-like social UI (SPhillips1337/im) with profiles, follows/friends, chat, messaging, image support, and a Twitter-style feed where OP posts show inline and comments are a click-through threaded view.

High-level approach (recommended)
- Non-invasive middleware: Read-only ingestion from Plebbit (DB or API) to avoid breaking the upstream. Normalize posts/users into a PlebX model, apply ranking, and serve the new UI and real-time services.
- Optional later: add controlled write-back to Plebbit after vetting permission, format and moderation concerns.

Key benefits
- Low-risk to existing Plebbit federation.
- Fast iteration: separate scaling for feed/ranking and original Plebbit services.
- Traceability: preserve external_plebbit_* fields so content remains auditable.

Architecture overview
- Source: Plebbit (bitsocialhq/5chan) via DB read or HTTP adapter.
- Middleware API (PlebX backend):
  - Ingest/adapter layer — canonicalize posts/users/threads.
  - Storage — Postgres (metadata), object store (S3), Redis (cache/queues), Qdrant/pgvector (optional for personalization).
  - Ranking service — port/adapt twitter/the-algorithm scoring as a microservice/library.
  - Worker queue — background tasks (image processing, indexing, notifications).
  - Realtime layer — WebSockets for chat/notifications.
  - Auth — OAuth2 bridge to Plebbit or native PlebX accounts mapped to Plebbit ids.
  - Moderation pipeline — pre/post checks, NSFW scanner, human review workflows.
- Frontend:
  - SPA (React/Vue) with timeline feed, profile pages, composer, thread view, and chat UI.

Data mapping (canonical PlebX fields)
- User: id, username, display_name, avatar_url, bio, external_plebbit_id
- Post: id, author_id, content, created_at, attachments[], reply_to, external_plebbit_post_id
- Thread: thread_id, root_post_id, participants[], last_activity_at
- Follow/Friends, Messages, Media as separate entities
- Keep external_* fields for traceability and optional write-back.

Ranking integration
- Implement deterministic scoring function (initially simplified) from twitter/the-algorithm:
  - Inputs: recency, author relevance, engagement, media, follows, trending signals.
  - Evaluate candidate pool (recent + cached high-engagement posts), score, sort, paginate.
  - Use Redis for caching and precompute expensive signals periodically.

Realtime & messaging
- WebSockets for presence, notifications, chat.
- Storage: Postgres for persistence, Redis pub/sub for delivery, background worker to persist and index.

Media handling
- Accept uploads via middleware, store in S3 (or local), generate thumbnails, perform NSFW/malware scans, attach safe preview metadata.

Auth & identity
- Recommended: OAuth2 bridge to Plebbit for identity continuity.
- Fallback: native PlebX accounts mapped to Plebbit IDs.

Moderation & safety
- Pre-publish filters: profanity, PII detection, image NSFW.
- Post-publish sampling and human review; reporting flows and kill-switch.
- Audit logs for all content and actions.

Deployment & infra
- Dev: Docker Compose (local Qdrant/Redis/Postgres).
- Staging/Prod: Kubernetes or managed services (RDS, Elasticache, S3).
- Observability: structured logs, Prometheus + Grafana, Sentry.
- CI: GitHub Actions (build, test, deploy).

Phased roadmap
Phase 0 — Discovery (1 week)
- Audit codebases: bitsocialhq/5chan, twitter/the-algorithm, SPhillips1337/im
- Decide read-only vs write-back strategy (default: read-only)
Phase 1 — MVP (2–4 weeks)
- Adapter that ingests Plebbit posts and exposes:
  - `GET /feed` (scored list)
  - `GET /post/:id` (thread)
  - `POST /post` (optionally creates local posts; optional write-back)
- Simple React UI showing timeline and thread view.
Phase 2 — Realtime & messaging (2–3 weeks)
- WebSockets, chat persistence, presence, notifications.
Phase 3 — Personalization & scaling (3–6 weeks)
- Embeddings, precomputation, caching, personalization, heavier infra.
Phase 4 — Hardening & launch
- Load testing, red-team, legal & compliance reviews, monitoring & runbooks.

MVP success criteria
- Feed generates in <500ms for 95% of requests (dev target).
- Users can view OP inline and navigate to thread comments.
- Image uploads with previews and NSFW scanning.
- Basic follow/friend model and notifications.

Open questions
- Read-only ingestion vs write-back now? (recommended: read-only)
- Preferred vector store: Qdrant or pgvector/Postgres?
- Host infra preference: self-managed Kubernetes or managed cloud services?

Next steps (immediate)
- Confirm read-only ingestion default.
- I will produce a starter scaffold: adapter + ranking microservice + frontend mockups.
- Create `PLAN.md` and `project.json` (I prepared contents — run commands below to write them on the server).

Files of interest
- /home/stephen/Documents/www/PlebX/AGENTS.md
- /home/stephen/Documents/www/PlebX/agent_spec.yaml
- https://github.com/bitsocialhq/5chan
- https://github.com/twitter/the-algorithm
- https://github.com/SPhillips1337/im

Contact
- Owner: stephen
- Repo contacts: owner emails will be set in project.json

Last updated: 2026-02-01T00:00:00Z
