"""Agentic AI Engine — Tool execution, agent orchestration, code completion.

Provides endpoints for:
  • POST /agentic/run — Execute an agentic AI workflow (Code Architect, Debugger, Test Generator)
  • GET /agentic/health/live — Liveness probe
  • GET /agentic/health/ready — Readiness probe
"""

from fastapi import FastAPI, status, WebSocket, HTTPException
from pydantic import BaseModel
import uuid

# ─── App ──────────────────────────
app = FastAPI(
    title="DAP Agentic AI Engine",
    description="Tool execution, agent orchestration, code completion",
    version="1.0.0",
)

# ─── Models ──────────────────────

class RunRequest(BaseModel):
    """POST /agentic/run — execute an agentic AI workflow."""
    sandbox_id: str
    query: str


class RunResponse(BaseModel):
    """POST /agentic/run — agent execution result."""
    request_id: str
    status: str  # processing | completed | failed
    agent_type: str  # Code Architect | Debugger | Test Generator
    result: dict


class StreamEvent(BaseModel):
    """WebSocket streaming event."""
    status: str  # running | completed | error
    agent: str
    step: int | None = None


# ─── Endpoints ──────────────────────

@app.post(
    "/run",
    response_model=RunResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute an agentic AI workflow",
)
async def run_agentic(request: RunRequest):
    """
    Execute an agentic AI workflow in the specified sandbox.

    In production:
      1. Validate sandbox access for the user
      2. Route to appropriate agent (Code Architect, Debugger, Test Generator)
      3. Execute in the sandbox and stream results via WebSocket
    """
    from src.agentic.agent_orchestrator import get_orchestrator, AgentType

    orchestrator = get_orchestrator()
    result = await orchestrator.execute_async(
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        user_query=request.query,
    )

    agent_type = AgentType[result["agent_type"]].name

    return RunResponse(
        request_id=result["request_id"],
        status="completed",
        agent_type=agent_type,
        result=result["result"],
    )


@app.get("/llm/status", status_code=status.HTTP_200_OK)
async def llm_status():
    """LLM backend status for the agentic engine."""
    from src.agentic.llm import get_llm_client

    client = get_llm_client()
    return {
        "configured": client.is_configured,
        "engine": "llm" if client.is_configured else "heuristic",
        "model": client.config.model,
        "base_url": client.config.base_url,
    }


@app.get("/health/live", status_code=status.HTTP_200_OK)
async def health_live():
    return {"status": "alive"}


@app.get("/health/ready", status_code=status.HTTP_200_OK)
async def health_ready():
    return {"status": "ready"}
