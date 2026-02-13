# Phase 2: Living Memory System

## Design Goals

1. **Token Efficient**: Minimize context window usage while maximizing relevance
2. **Predictive**: Load context before it's needed
3. **Self-Maintaining**: Consolidate, compress, and forget automatically
4. **Multi-Modal**: Facts, episodes, code patterns, and workflows

## Token Efficiency Strategy

### The Problem
Current systems stuff retrieved memories into context. With 200k tokens, you can fit ~150k words. Sounds like a lot until you realize:
- A week of development = 500+ memories
- Each memory averages 50-200 tokens
- Retrieval returns top-K results regardless of actual relevance
- Context gets polluted with marginally relevant information

### The Solution: Hierarchical Compression + Predictive Loading

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT BUDGET: 8,000 tokens                 │
│                    (reserved for memory injection)              │
├─────────────────────────────────────────────────────────────────┤
│ TIER 1: CRITICAL (2,000 tokens)                                │
│ • Active decisions affecting current file/task                  │
│ • Unresolved contradictions requiring attention                 │
│ • Recent errors and their fixes                                 │
├─────────────────────────────────────────────────────────────────┤
│ TIER 2: RELEVANT (3,000 tokens)                                │
│ • Predicted context based on current activity                   │
│ • Related architectural decisions                               │
│ • Team member preferences (if collaborating)                    │
├─────────────────────────────────────────────────────────────────┤
│ TIER 3: BACKGROUND (2,000 tokens)                              │
│ • Project-wide conventions (compressed)                         │
│ • Historical context summaries                                  │
│ • Workflow hints                                                │
├─────────────────────────────────────────────────────────────────┤
│ TIER 4: INDEX (1,000 tokens)                                   │
│ • Pointers to retrievable deep context                         │
│ • "Ask me about: auth, payments, deployment..."                │
│ • Enables on-demand expansion                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Memory Types

### 1. Facts (Atomic)
Compressed key-value pairs, not prose.

```yaml
# BAD: 47 tokens
"Tim mentioned that he strongly prefers using explicit error handling 
patterns with Result types instead of try-catch blocks, especially 
in TypeScript code where type safety is important."

# GOOD: 12 tokens
fact:
  key: "error_handling"
  value: "Result<T,E> over try-catch"
  scope: "typescript"
  confidence: 0.95
```

### 2. Episodes (Narrative Chunks)
Store once, summarize progressively.

```yaml
episode:
  id: "ep_auth_refactor_2026"
  title: "Auth Refactor"
  
  # Full detail (stored, not injected)
  full_narrative: "..." # 2000 tokens
  
  # Summary (injected to Tier 2)
  summary: "Replaced JWT with sessions due to token size issues" # 15 tokens
  
  # Compressed (injected to Tier 3)
  compressed: "auth: JWT→sessions (size)" # 5 tokens
  
  # Index entry (injected to Tier 4)
  index: "auth_refactor" # 1 token
  
  artifacts:
    - "ADR-012"
    - "commit:abc123"
```

### 3. Code Patterns (Structured)
AST-aware, not text descriptions.

```yaml
pattern:
  id: "pat_api_endpoint"
  trigger: "new_endpoint"
  
  # Structured template (expandable on demand)
  template:
    route: "{method} /api/{resource}"
    validation: "zod_schema"
    error_handling: "typed_result"
    response: "json_envelope"
  
  # Compressed hint for context
  hint: "endpoint: route→zod→result→json" # 6 tokens
```

### 4. Workflows (Procedural)
Step sequences, not descriptions.

```yaml
workflow:
  id: "wf_deploy"
  trigger: "deploy_request"
  
  steps: ["test", "build", "stage", "verify", "prod"]
  
  # Injected as single line
  hint: "deploy: test→build→stage→verify→prod" # 7 tokens
  
  # Expandable detail available
  details:
    test: "pnpm test --coverage >80%"
    build: "docker build -t app:${SHA}"
    # ...
```

## Core Components

### 1. Memory Lifecycle Manager

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEMORY LIFECYCLE MANAGER                     │
│                                                                 │
│  INGEST ──▶ EXTRACT ──▶ STORE ──▶ CONSOLIDATE ──▶ SERVE       │
│    │          │          │           │              │          │
│    ▼          ▼          ▼           ▼              ▼          │
│  raw       atomic      tiered     nightly        predictive    │
│  input     facts +     storage    compress       context       │
│            episodes    (hot/cold) + forget       assembly      │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Predictive Context Engine

Predicts what you'll need based on signals:

| Signal | Prediction | Action |
|--------|------------|--------|
| File opened | Related memories | Pre-load to Tier 2 |
| Branch checkout | Feature context | Load decisions, patterns |
| Error in console | Similar errors | Load fix patterns |
| Time of day | Routine tasks | Load relevant workflows |
| Collaborator joined | Their preferences | Load to Tier 2 |

```python
class PredictiveEngine:
    def on_file_open(self, filepath: str) -> ContextPrediction:
        # Extract signals
        module = extract_module(filepath)
        imports = extract_imports(filepath)
        recent_errors = get_recent_errors(filepath)
        
        # Predict needed context
        return ContextPrediction(
            tier1=self.get_critical(filepath, recent_errors),
            tier2=self.get_related(module, imports),
            tier3=self.get_background(module),
            tier4=self.get_index(module)
        )
```

### 3. Consolidation Engine

Runs on schedule (nightly or on-demand):

```python
class ConsolidationEngine:
    def consolidate(self):
        # 1. Deduplicate
        self.merge_similar_facts(threshold=0.92)
        
        # 2. Compress old memories
        self.summarize_episodes(older_than=days(7))
        self.compress_episodes(older_than=days(30))
        
        # 3. Promote/demote based on usage
        self.adjust_rankings()
        
        # 4. Detect and flag contradictions
        self.scan_contradictions()
        
        # 5. Active forgetting
        self.forget_superseded()
        self.forget_unused(older_than=days(90), usage_threshold=0)
        
        # 6. Link discovery
        self.discover_connections()
```

### 4. Contradiction Scanner

Continuous background process:

```python
class ContradictionScanner:
    def scan(self, new_memory: Memory) -> list[Contradiction]:
        # Find semantically similar memories
        similar = self.vector_search(new_memory.embedding, k=20)
        
        contradictions = []
        for existing in similar:
            if self.is_contradictory(new_memory, existing):
                contradictions.append(Contradiction(
                    memory_a=existing,
                    memory_b=new_memory,
                    detected_at=now(),
                    resolution=None
                ))
        
        return contradictions
    
    def is_contradictory(self, a: Memory, b: Memory) -> bool:
        # Use LLM to detect logical contradiction
        # Cache results to avoid repeated checks
        prompt = f"Are these contradictory?\nA: {a.compressed}\nB: {b.compressed}"
        return self.llm.judge(prompt, cache_key=f"{a.id}:{b.id}")
```

### 5. Usage Tracker

Track what actually gets used:

```python
class UsageTracker:
    def on_memory_retrieved(self, memory_id: str, context: str):
        self.log_retrieval(memory_id)
    
    def on_memory_cited(self, memory_id: str, action: str):
        # Memory influenced a real action
        self.log_citation(memory_id, action)
        self.boost_ranking(memory_id)
    
    def on_memory_ignored(self, memory_id: str):
        # Retrieved but not used
        self.log_ignore(memory_id)
        self.consider_demotion(memory_id)
```

## Context Assembly Algorithm

```python
def assemble_context(budget: int = 8000) -> str:
    """Assemble token-efficient context within budget."""
    
    context = ContextBuilder(budget)
    
    # Tier 1: Critical (25% of budget)
    tier1_budget = budget * 0.25
    context.add_tier1(
        active_decisions=get_active_decisions(current_file),
        unresolved_contradictions=get_contradictions(status="open"),
        recent_errors=get_recent_errors(hours=24),
        budget=tier1_budget
    )
    
    # Tier 2: Relevant (37.5% of budget)
    tier2_budget = budget * 0.375
    predictions = predictive_engine.predict(current_context)
    context.add_tier2(
        predicted=predictions.tier2,
        related_decisions=get_related_decisions(current_module),
        budget=tier2_budget
    )
    
    # Tier 3: Background (25% of budget)
    tier3_budget = budget * 0.25
    context.add_tier3(
        conventions=get_conventions_compressed(),
        history_summary=get_history_summary(current_module),
        workflow_hints=get_workflow_hints(current_activity),
        budget=tier3_budget
    )
    
    # Tier 4: Index (12.5% of budget)
    tier4_budget = budget * 0.125
    context.add_tier4(
        available_topics=get_topic_index(),
        expansion_hints=get_expansion_hints(),
        budget=tier4_budget
    )
    
    return context.render()
```

## Compression Strategies

### 1. Fact Compression
```
Original: "The team decided to use PostgreSQL as the primary database 
          because of its strong support for JSON operations and the 
          team's existing expertise with it."
          
Level 1:  "DB: PostgreSQL (JSON support, team expertise)"
Level 2:  "db:postgres(json,exp)"
Level 3:  "db:pg"
```

### 2. Episode Compression
```
Original: Full 2000-token session transcript

Level 1 (summary): "Debugged auth flow. Root cause: token expiry 
                   check used wrong timezone. Fixed by normalizing 
                   to UTC. Added regression test."

Level 2 (compressed): "auth_fix: tz→utc, +test"

Level 3 (index): "auth_tz_fix"
```

### 3. Pattern Compression
```
Original: Full code pattern with examples

Level 1 (template): Structured YAML with placeholders

Level 2 (hint): "endpoint: route→validate→handle→respond"

Level 3 (index): "api_pattern"
```

## Storage Schema

```sql
-- Core memories table
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    type ENUM('fact', 'episode', 'pattern', 'workflow'),
    
    -- Content at different compression levels
    content_full TEXT,           -- Original
    content_summary TEXT,        -- Level 1
    content_compressed TEXT,     -- Level 2
    content_index VARCHAR(50),   -- Level 3
    
    -- Embeddings (for each level)
    embedding_full VECTOR(768),
    embedding_summary VECTOR(768),
    
    -- Temporal
    created_at TIMESTAMP,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,          -- NULL = still valid
    last_accessed TIMESTAMP,
    
    -- Usage tracking
    retrieval_count INT DEFAULT 0,
    citation_count INT DEFAULT 0,
    ignore_count INT DEFAULT 0,
    
    -- Relationships
    supersedes UUID REFERENCES memories(id),
    superseded_by UUID REFERENCES memories(id),
    
    -- Scoping
    user_id VARCHAR(100),
    project_id VARCHAR(100),
    scope ENUM('user-private', 'project-shared', 'system')
);

-- Contradictions table
CREATE TABLE contradictions (
    id UUID PRIMARY KEY,
    memory_a UUID REFERENCES memories(id),
    memory_b UUID REFERENCES memories(id),
    detected_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution ENUM('a_wins', 'b_wins', 'both_valid', 'merged'),
    resolution_note TEXT
);

-- Episode artifacts
CREATE TABLE episode_artifacts (
    episode_id UUID REFERENCES memories(id),
    artifact_type ENUM('commit', 'pr', 'adr', 'file'),
    artifact_ref VARCHAR(200)
);
```

## API Endpoints

```yaml
# Context Assembly
POST /context/assemble
  body:
    budget: 8000
    signals:
      current_file: "src/auth/login.ts"
      recent_errors: ["TypeError: Cannot read property..."]
      activity: "debugging"
  response:
    context: "..."
    token_count: 7823
    tiers: {tier1: 1950, tier2: 2890, tier3: 1988, tier4: 995}

# Predictive Prefetch
POST /context/predict
  body:
    file_opened: "src/auth/login.ts"
  response:
    predicted_memories: [...]
    confidence: 0.87

# Consolidation (manual trigger)
POST /consolidate
  body:
    dry_run: true
  response:
    deduped: 23
    compressed: 156
    forgotten: 12
    contradictions_found: 3

# Contradiction Resolution
POST /contradictions/{id}/resolve
  body:
    resolution: "b_wins"
    note: "Migration completed, A is outdated"
```

## Token Budget Examples

### Scenario 1: Starting a new feature
```
Budget: 8000 tokens

Tier 1 (2000): 
  - Active ADRs for this module: 800 tokens
  - Recent team decisions: 600 tokens
  - Open questions/blockers: 400 tokens
  - Buffer: 200 tokens

Tier 2 (3000):
  - Related patterns: 1000 tokens
  - Similar past features: 1200 tokens
  - Dependency context: 600 tokens
  - Buffer: 200 tokens

Tier 3 (2000):
  - Project conventions: 800 tokens
  - Workflow hints: 400 tokens
  - Team preferences: 500 tokens
  - Buffer: 300 tokens

Tier 4 (1000):
  - Topic index: 600 tokens
  - Expansion pointers: 300 tokens
  - Buffer: 100 tokens

Total: 7800 tokens used, 200 buffer
```

### Scenario 2: Debugging an error
```
Budget: 8000 tokens

Tier 1 (3000): EXPANDED for debugging
  - Similar error patterns: 1500 tokens
  - Recent fixes in this file: 800 tokens
  - Known issues: 500 tokens
  - Buffer: 200 tokens

Tier 2 (2500):
  - Module context: 1000 tokens
  - Dependency issues: 800 tokens
  - Test failures history: 500 tokens
  - Buffer: 200 tokens

Tier 3 (1500): REDUCED
  - Debugging workflow: 600 tokens
  - Error handling conventions: 600 tokens
  - Buffer: 300 tokens

Tier 4 (1000):
  - Unchanged

Total: Dynamic rebalancing based on activity
```

## Implementation Phases

### Phase 2a: Core Infrastructure
- [ ] Tiered storage with compression levels
- [ ] Basic consolidation (dedup, compress)
- [ ] Usage tracking
- [ ] Context assembly with budgets

### Phase 2b: Intelligence Layer  
- [ ] Predictive context engine
- [ ] Contradiction detection
- [ ] Active forgetting
- [ ] Link discovery

### Phase 2c: Advanced Features
- [ ] Code pattern extraction (AST-aware)
- [ ] Workflow recording
- [ ] Re-embedding pipeline
- [ ] Multi-user memory merging

## Success Metrics

| Metric | Target |
|--------|--------|
| Context relevance (human eval) | >85% useful |
| Token efficiency | <8000 tokens for full context |
| Retrieval latency | <50ms |
| Prediction accuracy | >70% of needed context prefetched |
| Contradiction detection | >90% recall |
| False forgetting rate | <1% |
