FROM python:3.11-slim
WORKDIR /app

# Install minimal tooling for installer and runtime
RUN apt-get update && apt-get install -y --no-install-recommends     curl ca-certificates build-essential git nodejs npm   && rm -rf /var/lib/apt/lists/* || true

COPY runner.py /app/runner.py

# Ensure pip deps available (requests/watchdog)
RUN pip install --no-cache-dir requests watchdog || true

# Install OpenCode CLI during image build so it's present in container PATH
# NOTE: In production, verify the script integrity with a checksum or use a pinned version.
RUN curl -fsSL https://opencode.ai/install | bash || true

VOLUME ["/repo"]
CMD ["python", "/app/runner.py"]
