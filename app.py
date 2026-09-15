"""FastAPI service exposing the Strands agent over POST /chat."""

import logging
import os
import threading
from collections import OrderedDict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import telemetry
from agent import build_agent

telemetry.setup()

logger = logging.getLogger(__name__)

MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "1000"))

app = FastAPI(title="Strands + Bedrock Agent")

# session_id -> (agent, lock); an Agent carries its own history, so one per session.
_sessions: "OrderedDict[str, tuple]" = OrderedDict()
_registry_lock = threading.Lock()


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    response: str


def _session_for(session_id: str) -> tuple:
    with _registry_lock:
        entry = _sessions.pop(session_id, None)
        if entry is None:
            entry = (build_agent(stream_to_stdout=False), threading.Lock())
        _sessions[session_id] = entry
        while len(_sessions) > MAX_SESSIONS:
            _sessions.popitem(last=False)
    return entry


# Sync `def`: agent() blocks, so FastAPI runs it in a threadpool.
@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    agent, session_lock = _session_for(payload.session_id)
    try:
        # Serialize same-session calls; they share one message history.
        with session_lock:
            result = agent(payload.message)
    except Exception:
        logger.exception("chat invoke failed: session_id=%r", payload.session_id)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request",
        )
    return ChatResponse(response=str(result))
