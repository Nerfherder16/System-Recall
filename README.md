# Project Recall

**Self-hosted temporal knowledge memory system for Claude Code**

A production-ready memory infrastructure that gives Claude Code persistent, searchable, time-aware memory across sessions. Combines the best patterns from Supermemory, Mem0, and Zep's Graphiti into a fully self-hosted stack.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLAUDE CODE SESSION                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Session Start│───▶│  Active Work │───▶│ Session End  │      │
│  │   Injection  │    │              │    │   Capture    │      │
│  └──────┬───────┘    └──────────────┘    └──────┬───────┘      │
└─────────┼────────────────────────────────────────┼──────────────┘
          │                                        │
          ▼                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MEMORY ORCHESTRATOR                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │ Signal Detect  │  │ Fact Extract   │  │ Conflict Res   │    │
│  │ (keywords)     │  │ (atomic facts) │  │ (temporal)     │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │     Qdrant     │  │     Neo4j      │  │    Graphiti    │    │
│  │  (vectors)     │  │   (graph)      │  │  (temporal)    │    │
│  │  semantic      │  │  relationships │  │  bi-temporal   │    │
│  │  similarity    │  │  traversal     │  │  timestamps    │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Auto-Capture**: Automatically extracts and stores facts when sessions end
- **Context Injection**: Loads relevant memories at session start
- **Signal Detection**: Configurable keywords trigger immediate memory storage
- **Temporal Awareness**: Track when facts were learned AND when they were true
- **Triple Hybrid Retrieval**: Semantic + keyword + graph traversal (no LLM calls)
- **Multi-User Scoping**: Per-user, per-project, and shared team memories
- **Self-Hosted**: 100% local, nothing leaves your network

## Stack

| Component | Purpose | Port |
|-----------|---------|------|
| **Mem0** | Memory orchestration, fact extraction | 8080 |
| **Neo4j** | Graph relationships, Cypher queries | 7474/7687 |
| **Qdrant** | Vector storage, semantic search | 6333 |
| **Graphiti** | Temporal knowledge layer | (embedded) |
| **Orchestrator** | Session hooks, signal detection | 8000 |

## Quick Start

```bash
# Clone
git clone https://github.com/Nerfherder16/System-Recall.git
cd System-Recall

# Configure
cp .env.example .env
# Edit .env with your LLM endpoint, passwords, etc.

# Deploy
docker compose up -d

# Verify
curl http://localhost:8000/health
```

## Claude Code Integration

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "recall": {
      "command": "npx",
      "args": ["-y", "@mem0/mcp-server"],
      "env": {
        "MEM0_API_BASE": "http://localhost:8080",
        "MEM0_USER_ID": "${DEV_NAME}",
        "MEM0_PROJECT_ID": "your-project"
      }
    }
  }
}
```

## Memory Scopes

| Scope | Description | Example |
|-------|-------------|---------|
| `user-private` | Individual dev preferences | "Tim prefers explicit error handling" |
| `project-shared` | Team decisions, architecture | "Using SPL Token-2022 for transfer hooks" |
| `system` | Infrastructure, deployment | "Neo4j runs on port 7687" |

## Requirements

- Docker & Docker Compose
- 8GB+ RAM (16GB recommended)
- LLM endpoint for embeddings (local Ollama or API)

## Deployment

Designed for Proxmox LXC deployment with:
- ZFS storage pool for data persistence
- Sanoid/Syncoid for hourly snapshots
- Off-box replication to NAS

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for full Proxmox setup guide.

## License

MIT

---

*Built for the AI Dev Server project. Part of Tim's homelab infrastructure.*
