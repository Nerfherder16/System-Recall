"""
Project Recall - Memory Orchestrator

Handles session lifecycle, signal detection, and memory coordination
between Mem0, Neo4j, and Qdrant.
"""

import os
import re
import httpx
import structlog
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

MEM0_API_URL = os.getenv("MEM0_API_URL", "http://localhost:8080")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "recall2024")
SIGNAL_KEYWORDS = os.getenv("SIGNAL_KEYWORDS", "remember,decided,architecture,important").split(",")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
log = structlog.get_logger()

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------

class SessionStart(BaseModel):
    """Request to start a new session and get context injection."""
    user_id: str
    project_id: Optional[str] = "default"
    query: Optional[str] = None  # Optional context hint

class SessionEnd(BaseModel):
    """Request to end a session and capture memories."""
    user_id: str
    project_id: Optional[str] = "default"
    transcript: str  # Full session transcript
    
class MemoryCapture(BaseModel):
    """Request to immediately capture a memory (signal detection)."""
    user_id: str
    project_id: Optional[str] = "default"
    content: str
    scope: str = "user-private"  # user-private, project-shared, system

class SearchRequest(BaseModel):
    """Request to search memories."""
    query: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    limit: int = 10

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: dict

# -----------------------------------------------------------------------------
# Signal Detection
# -----------------------------------------------------------------------------

def detect_signals(text: str) -> list[str]:
    """
    Detect signal keywords in text that should trigger immediate memory capture.
    Returns list of matched signals.
    """
    signals = []
    text_lower = text.lower()
    for keyword in SIGNAL_KEYWORDS:
        if keyword.strip().lower() in text_lower:
            signals.append(keyword.strip())
    return signals

def extract_signal_context(text: str, signal: str, window: int = 200) -> str:
    """
    Extract context around a signal keyword for memory storage.
    """
    text_lower = text.lower()
    pos = text_lower.find(signal.lower())
    if pos == -1:
        return text[:window]
    
    start = max(0, pos - window // 2)
    end = min(len(text), pos + len(signal) + window // 2)
    return text[start:end].strip()

# -----------------------------------------------------------------------------
# Mem0 Client
# -----------------------------------------------------------------------------

async def mem0_add(content: str, user_id: str, project_id: str, metadata: dict = None):
    """Add a memory to Mem0."""
    async with httpx.AsyncClient() as client:
        payload = {
            "messages": [{"role": "user", "content": content}],
            "user_id": user_id,
            "metadata": {
                "project_id": project_id,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                **(metadata or {})
            }
        }
        response = await client.post(f"{MEM0_API_URL}/v1/memories/", json=payload)
        response.raise_for_status()
        return response.json()

async def mem0_search(query: str, user_id: str = None, project_id: str = None, limit: int = 10):
    """Search memories in Mem0."""
    async with httpx.AsyncClient() as client:
        params = {"query": query, "limit": limit}
        if user_id:
            params["user_id"] = user_id
        if project_id:
            params["filters"] = {"project_id": project_id}
        
        response = await client.post(f"{MEM0_API_URL}/v1/memories/search/", json=params)
        response.raise_for_status()
        return response.json()

async def mem0_get_all(user_id: str, project_id: str = None):
    """Get all memories for a user."""
    async with httpx.AsyncClient() as client:
        params = {"user_id": user_id}
        response = await client.get(f"{MEM0_API_URL}/v1/memories/", params=params)
        response.raise_for_status()
        return response.json()

# -----------------------------------------------------------------------------
# Application
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("recall_orchestrator_starting", keywords=SIGNAL_KEYWORDS)
    yield
    log.info("recall_orchestrator_stopping")

app = FastAPI(
    title="Project Recall - Orchestrator",
    description="Memory orchestration for Claude Code sessions",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check health of orchestrator and connected services."""
    services = {"orchestrator": "healthy"}
    
    # Check Mem0
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{MEM0_API_URL}/health")
            services["mem0"] = "healthy" if r.status_code == 200 else "unhealthy"
    except Exception:
        services["mem0"] = "unreachable"
    
    overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"
    
    return HealthResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=services
    )

@app.post("/session/start")
async def session_start(req: SessionStart):
    """
    Called at session start. Returns relevant context to inject.
    
    This is the "context injection" pattern from Supermemory.
    """
    log.info("session_start", user_id=req.user_id, project_id=req.project_id)
    
    try:
        # Get recent memories for this user + project
        memories = await mem0_get_all(req.user_id, req.project_id)
        
        # If there's a specific query/context hint, search for relevant memories
        relevant = []
        if req.query:
            search_results = await mem0_search(
                req.query, 
                user_id=req.user_id, 
                project_id=req.project_id,
                limit=5
            )
            relevant = search_results.get("results", [])
        
        return {
            "status": "ok",
            "user_id": req.user_id,
            "project_id": req.project_id,
            "memories_count": len(memories.get("results", [])),
            "context": {
                "recent": memories.get("results", [])[:10],
                "relevant": relevant
            }
        }
    except Exception as e:
        log.error("session_start_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/end")
async def session_end(req: SessionEnd):
    """
    Called at session end. Extracts and stores memories from transcript.
    
    This is the "auto-capture" pattern from Supermemory.
    """
    log.info("session_end", user_id=req.user_id, project_id=req.project_id, 
             transcript_length=len(req.transcript))
    
    try:
        # Detect any signal keywords in the transcript
        signals = detect_signals(req.transcript)
        captured = []
        
        # For each signal, extract context and store
        for signal in signals:
            context = extract_signal_context(req.transcript, signal)
            result = await mem0_add(
                content=context,
                user_id=req.user_id,
                project_id=req.project_id,
                metadata={"signal": signal, "source": "auto-capture"}
            )
            captured.append({"signal": signal, "memory_id": result.get("id")})
            log.info("memory_captured", signal=signal, user_id=req.user_id)
        
        # Also send full transcript to Mem0 for general fact extraction
        # (Mem0 will deduplicate and extract atomic facts)
        if len(req.transcript) > 100:  # Only if substantial content
            await mem0_add(
                content=f"Session transcript:\n{req.transcript[:5000]}",  # Limit size
                user_id=req.user_id,
                project_id=req.project_id,
                metadata={"source": "session-end", "full_transcript": True}
            )
        
        return {
            "status": "ok",
            "signals_detected": signals,
            "memories_captured": captured
        }
    except Exception as e:
        log.error("session_end_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/capture")
async def memory_capture(req: MemoryCapture):
    """
    Immediately capture a memory. Called when signal keywords detected mid-session.
    """
    log.info("memory_capture", user_id=req.user_id, scope=req.scope)
    
    try:
        result = await mem0_add(
            content=req.content,
            user_id=req.user_id,
            project_id=req.project_id,
            metadata={"scope": req.scope, "source": "explicit-capture"}
        )
        return {"status": "ok", "memory_id": result.get("id")}
    except Exception as e:
        log.error("memory_capture_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/search")
async def memory_search(req: SearchRequest):
    """
    Search memories with triple hybrid retrieval.
    """
    log.info("memory_search", query=req.query[:50], user_id=req.user_id)
    
    try:
        results = await mem0_search(
            query=req.query,
            user_id=req.user_id,
            project_id=req.project_id,
            limit=req.limit
        )
        return results
    except Exception as e:
        log.error("memory_search_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
