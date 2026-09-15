"""FastAPI service exposing the Strands agent over POST /chat."""

import logging
import threading
from collections import OrderedDict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from chat import build_agent

logger = logging.getLogger(__name__)

MAX_SESSIONS = 1000

app = FastAPI(title="Strands + Bedrock Agent")

# An Agent carries its own history, so each session gets one, in this process only.
_sessions = OrderedDict()
_registry_lock = threading.Lock()


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    response: str


class _Session:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.agent = None


def _session_for(session_id: str) -> _Session:
    with _registry_lock:
        session = _sessions.pop(session_id, None) or _Session()
        _sessions[session_id] = session
        while len(_sessions) > MAX_SESSIONS:
            _sessions.popitem(last=False)
    return session


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    session = _session_for(payload.session_id)
    try:
        with session.lock:
            if session.agent is None:
                session.agent = build_agent(stream_to_stdout=False)
            result = session.agent(payload.message)
    except Exception:
        logger.exception("chat failed: session_id=%r", payload.session_id)
        raise HTTPException(status_code=500, detail="Internal server error")
    return ChatResponse(response=str(result))
