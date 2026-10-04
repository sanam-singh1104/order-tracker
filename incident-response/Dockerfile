# Incident responder: a small stdlib Python service plus the Claude Code CLI,
# which it runs headless to investigate alerts.
FROM node:22-bookworm-slim

# curl and jq are for the agent's queries to the app, Loki, Tempo, and Prometheus.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 curl jq git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code@2.1.289 \
    && git config --system --add safe.directory '*'

WORKDIR /responder
COPY responder.py .
ENV PORT=8001 \
    INCIDENTS_DIR=/incidents \
    WORKSPACE_DIR=/workspace \
    PYTHONUNBUFFERED=1
EXPOSE 8001
CMD ["python3", "responder.py"]
