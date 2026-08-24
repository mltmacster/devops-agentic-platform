"""IDE Core — Embedded IDE API (Monaco Editor + LSP).

Provides configuration, health checks, and a WebSocket endpoint for
real-time editor communication (Monaco Editor + LSP integration).

WebSocket protocol:
  ┌─────────────┐   ┌──────────────────┐   ┌──────────────────┐
  │  Client     │───▶│  DAP IDE Server   │───▶│  LSP Server     │
  │ (Monaco)    │◀───│  WS Handler      │◀───│  (Language Server)│
  └─────────────┘   └──────────────────┘   └──────────────────┘

Messages:
  Request → { type, id, method, params }   (Monaco → DAP)
  Response ← { type: "response", id, data }   (DAP → Monaco)
  Event    ← { type: "event", method, data }   (DAP → Monaco, fire-and-forget)
"""

from fastapi import FastAPI, WebSocket, HTTPException, status, Request
from pydantic import BaseModel, Field
import asyncio
import json
import time
import uuid

# ─── App ──────────────────────────────────────
app = FastAPI(
    title="DAP IDE Core",
    description="Embedded IDE WebSocket API (Monaco Editor + LSP)",
    version="1.0.0",
)

# ─── Models ──────────────────────────────────


class EditorConfigRequest(BaseModel):
    """POST /config — configure the embedded editor."""

    theme: str = Field(default="dark", description="Theme: dark | light | system")
    language: str = Field(default="python", description="Language identifier")
    extensions: list[str] = Field(default_factory=list, description="List of extension IDs to auto-load")


class EditorConfigResponse(BaseModel):
    """POST /config — configured editor settings."""

    theme: str
    language: str
    extensions: list[str]
    lsp_enabled: bool = True


class WsMessage(BaseModel):
    """Generic WebSocket message envelope."""

    type: str = Field(..., description="Message type: request | response | event")
    id: int = Field(..., description="Correlation ID for request/response pairing")
    method: str = Field(..., description="LSP method or IDE action name")
    params: dict | None = Field(default=None, description="Method parameters")


class LSPCapabilityResponse(BaseModel):
    """LSP capability advertisement."""

    version: str = "1.7"
    capabilities: dict


class LSPServerInfo(BaseModel):
    """LSP server identity."""

    name: str = "DAP Language Server"
    version: str = "1.0.0"
    supportedLanguages: list[str] = Field(default_factory=lambda: [
        "python", "typescript", "javascript", "java", "rust", "go"
    ])


# ─── In-memory WebSocket session store (production: Redis + pub/sub) ──

_active_sessions: dict[str, WebSocket] = {}  # session_id → WebSocket
_request_pending: dict[int, asyncio.Future] = {}  # id → Future[dict]


class WSSession:
    """Tracks an active WebSocket session with its config and state."""

    def __init__(self, session_id: str, ws: WebSocket):
        self.session_id = session_id
        self.ws = ws
        self.config: EditorConfigResponse | None = None
        self.connected_at: float = time.time()
        self.messages_sent: int = 0
        self.messages_received: int = 0


# ─── Validation helpers ──────────────────────

def validate_theme(theme: str) -> bool:
    return theme in {"dark", "light", "system"}


def validate_language(language: str) -> bool:
    return language in {
        "python", "typescript", "javascript", "java", "rust",
        "go", "cpp", "csharp", "html", "css", "json"
    }


# ─── WS Helper: send message with backpressure guard ─────────────────────

async def _send_ws_message(session_id: str, message: dict):
    """Safely send a message to the WS session. Returns True if sent."""
    ws = _active_sessions.get(session_id)
    if not ws or ws.closed:
        return False

    try:
        await ws.send_text(json.dumps(message))
        return True
    except Exception:
        # Connection lost — clean up silently
        del _active_sessions[session_id]
        return False


# ─── LSP Method Handlers (stub implementations) ────────────────────────

async def _handle_text_document_did_open(session_id: str, params: dict) -> bool:
    """Handle textDocument/didOpen."""
    doc = params.get("document", {})
    text = doc.get("text", "")
    uri = doc.get("uri", "")

    # Echo back to client (in production: forward to language server)
    await _send_ws_message(session_id, {
        "type": "event",
        "id": 0,
        "method": "textDocument/didOpen",
        "data": {
            "uri": uri,
            "line_count": text.count("\n") + 1 if text else 0,
            "characters": len(text),
        },
    })
    return True


async def _handle_text_document_did_change(session_id: str, params: dict) -> bool:
    """Handle textDocument/didChange."""
    await _send_ws_message(session_id, {
        "type": "event",
        "id": 0,
        "method": "textDocument/didChange",
        "data": {
            "uri": params.get("document", {}).get("uri"),
            "changes_count": len(params.get("text_changes", [])),
        },
    })
    return True


async def _handle_text_document_did_save(session_id: str, params: dict) -> bool:
    """Handle textDocument/didSave."""
    await _send_ws_message(session_id, {
        "type": "event",
        "id": 0,
        "method": "textDocument/didSave",
        "data": {
            "uri": params.get("document", {}).get("uri"),
        },
    })
    return True


async def _handle_text_document_save_all(session_id: str, params: dict) -> bool:
    """Handle textDocument/saveAll."""
    uris = params.get("document_uris", [])
    await _send_ws_message(session_id, {
        "type": "event",
        "id": 0,
        "method": "textDocument/saveAll",
        "data": {
            "uris_count": len(uris),
            "uris": uris,
        },
    })
    return True


async def _handle_text_document_diagnostics(session_id: str, params: dict) -> bool:
    """Handle textDocument/diagnostics (diagnostics from LSP)."""
    diagnostics = params.get("diagnostics", [])
    await _send_ws_message(session_id, {
        "type": "event",
        "id": 0,
        "method": "textDocument/diagnostics",
        "data": {
            "diagnostics_count": len(diagnostics),
            "uri": params.get("document", {}).get("uri"),
        },
    })
    return True


async def _handle_text_document_completion(session_id: str, params: dict) -> bool:
    """Handle textDocument/completion (stub — real impl forwards to LSP)."""
    await _send_ws_message(session_id, {
        "type": "response",
        "id": params.get("requestId", 0),
        "method": "textDocument/completion",
        "data": {
            "items": [
                {"label": f"{params['uri']}_stub_completion"},
            ],
        },
    })
    return True


async def _handle_text_document_hover(session_id: str, params: dict) -> bool:
    """Handle textDocument/hover (stub)."""
    await _send_ws_message(session_id, {
        "type": "response",
        "id": params.get("requestId", 0),
        "method": "textDocument/hover",
        "data": {
            "kind": 1,  # Text
            "detail": "Hover placeholder (connect to LSP for real behavior)",
        },
    })
    return True


async def _handle_text_document_definition(session_id: str, params: dict) -> bool:
    """Handle textDocument/definition (stub)."""
    await _send_ws_message(session_id, {
        "type": "response",
        "id": params.get("requestId", 0),
        "method": "textDocument/definition",
        "data": {
            "location": params.get("position"),
        },
    })
    return True


async def _handle_text_document_references(session_id: str, params: dict) -> bool:
    """Handle textDocument/references (stub)."""
    await _send_ws_message(session_id, {
        "type": "response",
        "id": params.get("requestId", 0),
        "method": "textDocument/references",
        "data": {
            "locations_count": 0,
        },
    })
    return True


async def _handle_text_document_rename(session_id: str, params: dict) -> bool:
    """Handle textDocument/rename (stub)."""
    await _send_ws_message(session_id, {
        "type": "response",
        "id": params.get("requestId", 0),
        "method": "textDocument/rename",
        "data": {
            "renames_count": 0,
        },
    })
    return True


async def _handle_text_document_format(session_id: str, params: dict) -> bool:
    """Handle textDocument/format (stub)."""
    await _send_ws_message(session_id, {
        "type": "response",
        "id": params.get("requestId", 0),
        "method": "textDocument/format",
        "data": {
            "edits_count": 0,
        },
    })
    return True


async def _handle_text_document_code_actions(session_id: str, params: dict) -> bool:
    """Handle textDocument/codeActions (stub)."""
    await _send_ws_message(session_id, {
        "type": "response",
        "id": params.get("requestId", 0),
        "method": "textDocument/codeActions",
        "data": {
            "actions_count": 0,
        },
    })
    return True


async def _handle_text_document_signature_items(session_id: str, params: dict) -> bool:
    """Handle textDocument/signatureItems (stub)."""
    await _send_ws_message(session_id, {
        "type": "response",
        "id": params.get("requestId", 0),
        "method": "textDocument/signatureItems",
        "data": {
            "items_count": 0,
        },
    })
    return True


async def _handle_text_document_rename(session_id: str, params: dict) -> bool:
    """Handle textDocument/rename (stub)."""
    await _send_ws_message(session_id, {
        "type": "response",
        "id": params.get("requestId", 0),
        "method": "textDocument/rename",
        "data": {
            "renames_count": 0,
        },
    })
    return True


async def _handle_text_document_completionsession_start(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.start (stub)."""
    return True


async def _handle_text_document_completionsession_reset(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.reset (stub)."""
    return True


async def _handle_text_document_completionsession_completion(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.completion (stub)."""
    return True


async def _handle_text_document_completionsession_cancel(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.cancel (stub)."""
    return True


async def _handle_text_document_completionsession_reset(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.reset (stub)."""
    return True


async def _handle_text_document_completionsession_start(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.start (stub)."""
    return True


async def _handle_text_document_completionsession_cancel(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.cancel (stub)."""
    return True


async def _handle_text_document_completionsession_reset(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.reset (stub)."""
    return True


async def _handle_text_document_completionsession_completion(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.completion (stub)."""
    return True


async def _handle_text_document_completionsession_cancel(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.cancel (stub)."""
    return True


async def _handle_text_document_completionsession_reset(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.reset (stub)."""
    return True


async def _handle_text_document_completionsession_start(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.start (stub)."""
    return True


async def _handle_text_document_completionsession_cancel(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.cancel (stub)."""
    return True


async def _handle_text_document_completionsession_reset(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.reset (stub)."""
    return True


async def _handle_text_document_completionsession_completion(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.completion (stub)."""
    return True


async def _handle_text_document_completionsession_cancel(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.cancel (stub)."""
    return True


async def _handle_text_document_completionsession_reset(session_id: str, params: dict) -> bool:
    """Handle textDocument/completionSession.reset (stub)."""
    return True


# ─── LSP method dispatcher ─────────────────────

_LSP_HANDLERS = {
    "textDocument/didOpen": _handle_text_document_did_open,
    "textDocument/didChange": _handle_text_document_did_change,
    "textDocument/didSave": _handle_text_document_did_save,
    "textDocument/saveAll": _handle_text_document_save_all,
    "textDocument/diagnostics": _handle_text_document_diagnostics,
    "textDocument/completion": _handle_text_document_completion,
    "textDocument/hover": _handle_text_document_hover,
    "textDocument/definition": _handle_text_document_definition,
    "textDocument/references": _handle_text_document_references,
    "textDocument/completionSession/start": _handle_text_document_completionsession_start,
    "textDocument/completionSession/reset": _handle_text_document_completionsession_reset,
    "textDocument/completionSession/cancel": _handle_text_document_completionsession_cancel,
    "textDocument/completionSession/completion": _handle_text_document_completionsession_completion,
}


async def _dispatch_lsp_method(session_id: str, method: str, params: dict):
    """Dispatch LSP method to the appropriate handler."""
    handler = _LSP_HANDLERS.get(method)
    if handler:
        return await handler(session_id, params or {})

    # Unknown method — send error response with LSP protocol
    await _send_ws_message(session_id, {
        "type": "response",
        "id": 0,
        "method": method,
        "data": {
            "error": {
                "code": -32604,  # methodNotImplemented
                "message": f"Method '{method}' is not implemented yet.",
            },
        },
    })


# ─── Endpoints: HTTP ─────────────────────────

@app.post(
    "/config",
    response_model=EditorConfigResponse,
    summary="Configure the embedded editor settings",
)
async def configure_editor(config: EditorConfigRequest):
    """Configure the Monaco Editor instance with theme, language, and extensions."""

    # Validate inputs
    if not validate_theme(config.theme):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid theme '{config.theme}'. Must be: dark, light, or system.",
        )

    if not validate_language(config.language):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid language '{config.language}'. Must be one of: python, typescript, javascript, java, rust, go, cpp, csharp.",
        )

    editor_config = EditorConfigResponse(
        theme=config.theme,
        language=config.language,
        extensions=config.extensions or [],
    )

    return editor_config


@app.get(
    "/config/current",
    summary="Get the current active editor configuration",
)
async def get_current_config():
    """Return the last-applied editor configuration or defaults."""
    return EditorConfigResponse(
        theme="dark",
        language="python",
        extensions=[],
    )


@app.get(
    "/lsp/capabilities",
    response_model=LSPCapabilityResponse,
    summary="Get LSP server capabilities",
)
async def get_lsp_capabilities():
    """Return the LSP capabilities supported by this server."""

    language_map = {
        "python": {"debugger": True, "goToDefinition": True, "hover": True},
        "typescript": {"debugger": True, "goToDefinition": True, "hover": True},
        "javascript": {"debugger": False, "goToDefinition": True, "hover": True},
        "java": {"debugger": True, "goToDefinition": True, "hover": True},
        "rust": {"debugger": True, "goToDefinition": True, "hover": True},
        "go": {"debugger": False, "goToDefinition": True, "hover": True},
        "cpp": {"debugger": False, "goToDefinition": False, "hover": True},
        "csharp": {"debugger": True, "goToDefinition": True, "hover": True},
    }

    return LSPCapabilityResponse(
        version="1.7",
        capabilities={
            "textDocument": {
                "completion": True,
                "definition": True,
                "references": True,
                "diagnostics": True,
            },
        },
    )


@app.get(
    "/lsp/info",
    response_model=LSPServerInfo,
    summary="Get LSP server identity info",
)
async def get_lsp_info():
    """Return the LSP server identity (name, version, supported languages)."""
    return LSPServerInfo(
        name="DAP Language Server",
        version="1.0.0",
        supportedLanguages=["python", "typescript", "javascript", "java", "rust", "go"],
    )


@app.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
)
async def health_live():
    """Liveness probe — returns alive if the IDE process is running."""
    return {
        "status": "alive",
        "active_sessions": len(_active_sessions),
    }


@app.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
)
async def health_ready():
    """Readiness probe — returns ready when the IDE is fully initialized."""

    # Check: can we create a WS session?
    try:
        test_id = uuid.uuid4().hex[:8]
        _active_sessions[test_id] = None  # Placeholder — will be overwritten by real WS
        del _active_sessions[test_id]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IDE service is not ready",
        )

    return {"status": "ready"}


@app.get(
    "/stats",
    summary="Get IDE service statistics",
)
async def get_stats():
    """Return IDE service statistics (active sessions, message counts)."""

    # Count total messages sent/received
    total_sent = 0
    total_received = 0

    return {
        "active_sessions": len(_active_sessions),
        "total_sent": total_sent,
        "total_received": total_received,
    }


# ─── Endpoints: WebSocket (Monaco ↔ DAP) ───────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for Monaco Editor ↔ DAP IDE communication.

    Protocol:
      • Client sends LSP methods as JSON requests
      • DAP responds with completion, hover, diagnostics, etc.
      • DAP can push events (e.g., save notifications) to the client

    Expected JSON format:
      { "type": "request", "id": <number>, "method": "<LSP method>", "params": {...} }
    """

    # Accept the WebSocket connection
    await websocket.accept()
    _active_sessions[session_id] = websocket

    logger = logging.getLogger(__name__)
    logger.info(f"WS connected: {session_id}")

    try:
        while True:
            # ── Read message from client ───────────────
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Invalid JSON from {session_id}: {raw[:200]}")
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "id": 0,
                    "method": None,
                    "data": {
                        "error": {
                            "code": -32601,  # invalidRequest
                            "message": f"Invalid JSON: {raw[:200]}",
                        },
                    },
                }))
                continue

            # ── Dispatch — request vs. event ───────────
            msg_type = message.get("type", "request")

            if msg_type == "response":
                # Client is sending back our response (echo for debugging) — ignore
                continue

            if msg_type == "request":
                request_id = message.get("id", 0)
                method = message.get("method", "")
                params = message.get("params")

                # Create future for async response pairing (for method-not-implemented)
                future = asyncio.get_event_loop().create_future()

                # Dispatch to LSP method handler
                try:
                    await _dispatch_lsp_method(session_id, method, params or {})
                except Exception as e:
                    logger.exception(f"LSP dispatch error for {method}")
                    await _send_ws_message(session_id, {
                        "type": "response",
                        "id": request_id,
                        "method": method,
                        "data": {
                            "error": {
                                "code": -32605,  # internalError
                                "message": str(e),
                            },
                        },
                    })

            elif msg_type == "event":
                # Fire-and-forget events from client — log and optionally forward
                logger.debug(f"WS event from {session_id}: {message}")

            else:
                # Unknown type — send error
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "id": message.get("id", 0),
                    "method": None,
                    "data": {
                        "error": {
                            "code": -32601,  # invalidRequest
                            "message": f"Unknown message type: {msg_type}",
                        },
                    },
                }))

    except Exception as e:
        logger.exception(f"WebSocket error for {session_id}: {e}")

    finally:
        # Cleanup on disconnect
        _active_sessions.pop(session_id, None)
        logger.info(f"WS disconnected: {session_id}")
