# Architecture

## Overview

Project Recall is a self-hosted memory system designed to give AI coding assistants (primarily Claude Code) persistent, searchable, time-aware memory across sessions.

## Design Principles

1. **Self-Hosted First**: All data stays on your infrastructure
2. **LLM Agnostic**: Works with Ollama, OpenAI, Anthropic, or any compatible API
3. **Triple Hybrid Retrieval**: Semantic + keyword + graph traversal
4. **Temporal Awareness**: Track when facts were learned AND when they were true
5. **Zero LLM Calls at Query Time**: Pre-computed embeddings and graph traversal

## Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Claude Code  │    │   CLI Tool   │    │   REST API   │      │
│  │  (via MCP)   │    │              │    │              │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
└─────────┼────────────────────┼────────────────────┼─────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (FastAPI)                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │ Session Hooks  │  │ Signal Detect  │  │ Memory Router  │    │
│  │ start/end      │  │ keywords       │  │ CRUD ops       │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MEM0 (Memory Layer)                        │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │ Fact Extract   │  │ Deduplication  │  │ Conflict Res   │    │
│  │ (LLM-powered)  │  │ (embedding)    │  │ (temporal)     │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │     Qdrant     │  │     Neo4j      │  │   (Graphiti)   │    │
│  │   (vectors)    │  │    (graph)     │  │  (temporal)    │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Memory Storage

1. Content arrives (session end, explicit capture, or signal detection)
2. Orchestrator detects signal keywords and extracts context
3. Mem0 receives content and extracts atomic facts using LLM
4. Facts are embedded and checked for duplicates
5. New facts stored in Qdrant (vectors) and Neo4j (relationships)
6. Temporal metadata attached (captured_at, valid_from, valid_to)

### Memory Retrieval

1. Query arrives (session start context injection or explicit search)
2. Query embedded using same model as storage
3. Triple hybrid search:
   - **Semantic**: Qdrant similarity search
   - **Keyword**: BM25-style text matching
   - **Graph**: Neo4j relationship traversal
4. Results merged, ranked, and deduplicated
5. Returned to client (no LLM call required)

## Memory Scopes

| Scope | Description | Use Case |
|-------|-------------|----------|
| `user-private` | Individual user preferences | "I prefer explicit error handling" |
| `project-shared` | Team decisions for a project | "We decided to use SPL Token-2022" |
| `system` | Global infrastructure knowledge | "The API runs on port 8080" |

## Signal Keywords

Configurable keywords that trigger immediate memory capture:

- `remember` - Explicit request to store
- `decided` - Architectural decisions
- `architecture` - Design patterns
- `important` - Critical information
- `don't forget` - Reminders
- `note to self` - Personal notes
- `bug fix` - Issue resolutions
- `breaking change` - API changes

## Temporal Tracking

Each memory has two timestamps:

- **captured_at**: When the memory was stored
- **valid_at**: When the fact was true (defaults to captured_at)

This enables queries like:
- "What did we know about X on date Y?"
- "How has our understanding of X evolved?"
- "What changed between version 1 and version 2?"

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Memory storage | 200-500ms | LLM fact extraction |
| Memory search | 10-50ms | No LLM, pure retrieval |
| Session start injection | 50-100ms | Pre-computed context |
| Signal detection | <1ms | Regex matching |

## Scaling

- **Qdrant**: Horizontally scalable, supports sharding
- **Neo4j**: Vertical scaling, read replicas for queries
- **Orchestrator**: Stateless, can run multiple instances

## Security

- All services run in Docker with no external exposure by default
- Neo4j and Qdrant have authentication enabled
- No data leaves your network (when using local LLM)
- API keys stored in environment variables, not in code
