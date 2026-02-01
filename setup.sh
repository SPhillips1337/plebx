#!/usr/bin/env bash
set -e
# Copies .env.example to .env if not exists
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Copied .env.example -> .env. Please edit .env to add secrets (OPENAI_API_KEY)."
fi
# Build and start dev stack
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install Docker and docker-compose before running this script."
  exit 1
fi

docker compose build --pull
docker compose up -d

echo "Dev stack started. API available at http://localhost:8000/health (on the host)."
