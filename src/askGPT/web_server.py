"""
FastAPI web server for askGPT chatbot.

Provides REST API, WebSocket, and SSE endpoints for integrating askGPT
into web applications and services.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .api import AskGPTClient
from .modules.data_types import ChatMessage, PromptNanoAgentResponse
from .modules.session_manager import Session

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="askGPT Chatbot API",
    description="REST API and WebSocket interface for askGPT AI agent",
    version="2.0.0",
)

# CORS middleware configuration
# In production, configure allowed_origins appropriately
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global client instance
_client: Optional[AskGPTClient] = None


def get_client() -> AskGPTClient:
    """Get or create the global AskGPTClient instance."""
    global _client
    if _client is None:
        _client = AskGPTClient()
    return _client


# Request/Response Models


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., description="User's message/prompt", min_length=1)
    session_id: Optional[str] = Field(None, description="Optional session ID to continue conversation")
    model: Optional[str] = Field(None, description="Optional model override")
    provider: Optional[str] = Field(None, description="Optional provider override")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum response tokens")
    agent_name: Optional[str] = Field(None, description="Optional agent personality")
    read_only: bool = Field(False, description="Disable write operations")
    allowed_tools: Optional[List[str]] = Field(None, description="List of allowed tools")
    blocked_tools: Optional[List[str]] = Field(None, description="List of blocked tools")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Session ID for this conversation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    success: bool = Field(True, description="Whether the request succeeded")


class SessionResponse(BaseModel):
    """Response model for session information."""

    session_id: str
    created_at: str
    last_updated: str
    provider: str
    model: str
    message_count: int
    metadata: Dict[str, Any]


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    provider: Optional[str] = Field(None, description="Provider name")
    model: Optional[str] = Field(None, description="Model name")
    session_id: Optional[str] = Field(None, description="Optional custom session ID")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = "healthy"
    version: str = "2.0.0"


# REST Endpoints


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Send a chat message and get response.

    This endpoint processes a chat message and returns the agent's response.
    If a session_id is provided, the conversation continues from that session.
    """
    try:
        client = get_client()

        # Prepare kwargs for chat method
        kwargs = {}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        if request.agent_name is not None:
            kwargs["agent_name"] = request.agent_name
        if request.read_only:
            kwargs["read_only"] = True
        if request.allowed_tools is not None:
            kwargs["allowed_tools"] = request.allowed_tools
        if request.blocked_tools is not None:
            kwargs["blocked_tools"] = request.blocked_tools

        # Execute chat
        response = await client.chat(
            message=request.message,
            session_id=request.session_id,
            model=request.model,
            provider=request.provider,
            **kwargs,
        )

        if not response.success:
            raise HTTPException(
                status_code=500,
                detail=response.error or "Agent execution failed",
            )

        # Get session ID from response metadata or create new one
        session_id = request.session_id
        if not session_id and client.session_manager.current_session:
            session_id = client.session_manager.current_session.session_id

        return ChatResponse(
            response=response.result or "",
            session_id=session_id or "",
            metadata=response.metadata,
            success=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/sessions", response_model=List[SessionResponse])
async def list_sessions(limit: int = 10):
    """List recent sessions."""
    try:
        client = get_client()
        sessions = client.list_sessions(limit=limit)

        return [
            SessionResponse(
                session_id=session.session_id,
                created_at=session.created_at,
                last_updated=session.last_updated,
                provider=session.provider,
                model=session.model,
                message_count=len(session.conversation),
                metadata=session.metadata,
            )
            for session in sessions
        ]
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session details by ID."""
    try:
        client = get_client()
        session = client.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        return SessionResponse(
            session_id=session.session_id,
            created_at=session.created_at,
            last_updated=session.last_updated,
            provider=session.provider,
            model=session.model,
            message_count=len(session.conversation),
            metadata=session.metadata,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/sessions", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new session."""
    try:
        client = get_client()
        session = client.create_session(
            provider=request.provider,
            model=request.model,
            session_id=request.session_id,
        )

        return SessionResponse(
            session_id=session.session_id,
            created_at=session.created_at,
            last_updated=session.last_updated,
            provider=session.provider,
            model=session.model,
            message_count=len(session.conversation),
            metadata=session.metadata,
        )
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    try:
        client = get_client()
        session = client.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Delete session file
        session_file = client.session_manager.storage_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

        return {"message": f"Session {session_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/models")
async def list_models():
    """List available models from configuration."""
    try:
        client = get_client()
        config = client.config

        models = {}
        for provider_name, provider_config in config.providers.items():
            models[provider_name] = {
                "known_models": provider_config.known_models,
                "allow_unknown_models": provider_config.allow_unknown_models,
                "discover_models": provider_config.discover_models,
            }

        return {
            "default_provider": config.default_provider,
            "default_model": config.default_model,
            "providers": models,
            "model_aliases": config.model_aliases,
        }
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# WebSocket Endpoint


@app.websocket("/api/v1/chat/stream")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat.

    Protocol:
    - Client sends: {"message": str, "session_id": Optional[str], ...}
    - Server sends: {"chunk": str, "done": bool, "session_id": str}
    """
    await websocket.accept()
    client = get_client()
    session_id = None

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                await websocket.send_json(
                    {"error": "Message is required", "done": True}
                )
                continue

            # Extract parameters
            session_id = data.get("session_id")
            model = data.get("model")
            provider = data.get("provider")
            kwargs = {}
            if "temperature" in data:
                kwargs["temperature"] = data["temperature"]
            if "max_tokens" in data:
                kwargs["max_tokens"] = data["max_tokens"]
            if "agent_name" in data:
                kwargs["agent_name"] = data["agent_name"]

            # Stream response
            async for chunk in client.chat_stream(
                message, session_id=session_id, model=model, provider=provider, **kwargs
            ):
                # Get current session ID
                current_session_id = session_id
                if not current_session_id and client.session_manager.current_session:
                    current_session_id = client.session_manager.current_session.session_id

                await websocket.send_json(
                    {
                        "chunk": chunk,
                        "done": False,
                        "session_id": current_session_id or "",
                    }
                )

            # Send final message
            current_session_id = session_id
            if not current_session_id and client.session_manager.current_session:
                current_session_id = client.session_manager.current_session.session_id

            await websocket.send_json(
                {
                    "chunk": "",
                    "done": True,
                    "session_id": current_session_id or "",
                }
            )

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket chat: {e}", exc_info=True)
        try:
            await websocket.send_json(
                {"error": str(e), "done": True}
            )
        except Exception:
            pass
        await websocket.close()


# SSE Endpoint


@app.get("/api/v1/chat/stream")
async def sse_chat_stream(
    message: str,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
):
    """
    Server-Sent Events endpoint for streaming chat.

    Query parameters:
    - message: The user's message (required)
    - session_id: Optional session ID
    - model: Optional model override
    - provider: Optional provider override
    """
    client = get_client()

    async def generate():
        try:
            async for chunk in client.chat_stream(
                message, session_id=session_id, model=model, provider=provider
            ):
                # Get current session ID
                current_session_id = session_id
                if not current_session_id and client.session_manager.current_session:
                    current_session_id = client.session_manager.current_session.session_id

                data = json.dumps(
                    {
                        "chunk": chunk,
                        "done": False,
                        "session_id": current_session_id or "",
                    }
                )
                yield f"data: {data}\n\n"

            # Send final message
            current_session_id = session_id
            if not current_session_id and client.session_manager.current_session:
                current_session_id = client.session_manager.current_session.session_id

            final_data = json.dumps(
                {
                    "chunk": "",
                    "done": True,
                    "session_id": current_session_id or "",
                }
            )
            yield f"data: {final_data}\n\n"

        except Exception as e:
            logger.error(f"Error in SSE stream: {e}", exc_info=True)
            error_data = json.dumps({"error": str(e), "done": True})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
