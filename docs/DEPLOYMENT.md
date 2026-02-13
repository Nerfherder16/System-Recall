# Deployment Guide

## Quick Start (Docker)

```bash
git clone https://github.com/Nerfherder16/System-Recall.git
cd System-Recall
cp .env.example .env
# Edit .env with your configuration
docker compose up -d
```

## Requirements

- Docker & Docker Compose v2
- 8GB RAM minimum (16GB recommended)
- LLM endpoint (local Ollama or cloud API)

## LLM Options

### Option 1: Local Ollama (Recommended for Privacy)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull llama3.1:8b      # For fact extraction
ollama pull nomic-embed-text  # For embeddings

# Update .env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b
EMBEDDING_MODEL=nomic-embed-text
```

### Option 2: OpenAI API

```bash
# Update .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
```

### Option 3: Anthropic API

```bash
# Update .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key-here
LLM_MODEL=claude-sonnet-4-20250514
# Note: Still needs OpenAI for embeddings
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_MODEL=text-embedding-3-small
```

## Proxmox LXC Deployment

For production deployments on Proxmox:

### 1. Create LXC Container

```bash
# On Proxmox host
pct create 200 local:vztmpl/ubuntu-24.04-standard_24.04-1_amd64.tar.zst \
  --hostname recall \
  --memory 8192 \
  --cores 4 \
  --rootfs local-zfs:32 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1
```

### 2. Install Docker in LXC

```bash
pct start 200
pct enter 200

# Inside LXC
apt update && apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 3. Deploy Project Recall

```bash
cd /opt
git clone https://github.com/Nerfherder16/System-Recall.git
cd System-Recall
cp .env.example .env
nano .env  # Configure your settings
docker compose up -d
```

### 4. ZFS Snapshots (Optional but Recommended)

Install Sanoid for automated snapshots:

```bash
apt install -y sanoid
```

Create `/etc/sanoid/sanoid.conf`:

```ini
[local-zfs/subvol-200-disk-0]
  use_template = recall
  recursive = yes

[template_recall]
  hourly = 24
  daily = 30
  weekly = 4
  monthly = 3
  autosnap = yes
  autoprune = yes
```

Enable the timer:

```bash
systemctl enable --now sanoid.timer
```

## Claude Code Integration

### MCP Configuration

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "recall": {
      "command": "npx",
      "args": ["-y", "@mem0/mcp-server"],
      "env": {
        "MEM0_API_BASE": "http://your-recall-server:8080",
        "MEM0_USER_ID": "${USER}",
        "MEM0_PROJECT_ID": "your-project"
      }
    }
  }
}
```

### Session Hooks (Optional)

For automatic session capture, add to `.claude/hooks.json`:

```json
{
  "hooks": {
    "SessionEnd": [{
      "command": "curl -X POST http://your-recall-server:8000/session/end -H 'Content-Type: application/json' -d '{\"user_id\": \"${USER}\", \"project_id\": \"your-project\", \"transcript\": \"${SESSION_TRANSCRIPT}\"}'",
      "description": "Capture session memories"
    }]
  }
}
```

## Verification

Check all services are healthy:

```bash
# Service health
curl http://localhost:8000/health

# Test memory storage
curl -X POST http://localhost:8000/memory/capture \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "content": "This is a test memory", "scope": "user-private"}'

# Test memory search
curl -X POST http://localhost:8000/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test memory", "user_id": "test"}'
```

## Troubleshooting

### Services won't start
```bash
docker compose logs -f
```

### Neo4j connection issues
```bash
docker exec -it recall-neo4j cypher-shell -u neo4j -p your-password
```

### Qdrant issues
```bash
curl http://localhost:6333/collections
```

### Memory not being stored
Check orchestrator logs:
```bash
docker logs -f recall-orchestrator
```
