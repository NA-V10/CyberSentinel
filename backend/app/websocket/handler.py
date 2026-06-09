"""
WebSocket connection manager and status broadcaster for CyberSentinel AI.

Manages active WebSocket sessions, provides a typed step enum, and
exposes helpers for sending structured JSON status updates to clients.
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

# ---------------------------------------------------------------------------
# Analysis step enumeration
# ---------------------------------------------------------------------------


class AnalysisStep(str, Enum):
    """Ordered steps in the multi-agent incident analysis pipeline."""

    VALIDATION = "validation"
    CLASSIFICATION = "classification"
    RETRIEVAL = "retrieval"
    GRAPH_EXPANSION = "graph_expansion"
    MITIGATION = "mitigation"
    ESCALATION = "escalation"
    EXPLANATION = "explanation"
    JUDGE = "judge"
    COMPLETE = "complete"
    ERROR = "error"


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Manages active WebSocket connections keyed by session_id.

    Thread-safe for async use (single-threaded event loop assumed).
    """

    def __init__(self) -> None:
        # session_id -> WebSocket
        self._connections: Dict[str, WebSocket] = {}
        # session_id -> asyncio.Lock (prevents interleaved sends)
        self._locks: Dict[str, asyncio.Lock] = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Accept the WebSocket handshake and register the session.

        Parameters
        ----------
        session_id:
            Unique session identifier (from the URL path).
        websocket:
            The incoming :class:`~fastapi.WebSocket` connection.
        """
        await websocket.accept()
        self._connections[session_id] = websocket
        self._locks[session_id] = asyncio.Lock()
        logger.info("WebSocket connected", session_id=session_id)

    async def disconnect(self, session_id: str) -> None:
        """Remove and clean up a WebSocket session.

        Safe to call even if *session_id* is not registered.
        """
        ws = self._connections.pop(session_id, None)
        self._locks.pop(session_id, None)

        if ws is not None:
            try:
                await ws.close()
            except Exception:
                pass  # already closed

        logger.info("WebSocket disconnected", session_id=session_id)

    def is_connected(self, session_id: str) -> bool:
        """Return ``True`` if the session has an active WebSocket."""
        return session_id in self._connections

    @property
    def active_sessions(self) -> list[str]:
        """Return the list of currently connected session IDs."""
        return list(self._connections.keys())

    # ------------------------------------------------------------------
    # Message sending
    # ------------------------------------------------------------------

    async def send_json(
        self,
        session_id: str,
        payload: Dict[str, Any],
    ) -> bool:
        """Send a JSON-serialisable payload to the session.

        Uses a per-session lock to prevent interleaved writes.

        Parameters
        ----------
        session_id:
            Target session.
        payload:
            Any JSON-serialisable dict.

        Returns
        -------
        bool
            ``True`` if the message was sent, ``False`` if the session is
            gone or the send fails.
        """
        ws = self._connections.get(session_id)
        if ws is None:
            logger.warning("send_json — session not found", session_id=session_id)
            return False

        lock = self._locks.get(session_id)
        if lock is None:
            logger.warning("send_json — no lock for session", session_id=session_id)
            return False

        try:
            async with lock:
                await ws.send_json(payload)
            return True
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected during send", session_id=session_id)
            await self.disconnect(session_id)
            return False
        except Exception as exc:
            logger.error(
                "WebSocket send failed",
                session_id=session_id,
                error=str(exc),
            )
            await self.disconnect(session_id)
            return False

    async def send_status(
        self,
        session_id: str,
        step: AnalysisStep | str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a structured status update to a session.

        Serialises the payload as::

            {
                "type": "status",
                "step": "<AnalysisStep value>",
                "message": "<human-readable message>",
                "data": { ... }   # optional
            }

        Parameters
        ----------
        session_id:
            Target session.
        step:
            The current analysis step (as :class:`AnalysisStep` or a raw string).
        message:
            A human-readable status description shown to the analyst.
        data:
            Optional structured payload attached to the status event.

        Returns
        -------
        bool
            ``True`` if the message was delivered.
        """
        step_value = step.value if isinstance(step, AnalysisStep) else step
        payload: Dict[str, Any] = {
            "type": "status",
            "step": step_value,
            "message": message,
        }
        if data is not None:
            payload["data"] = data

        logger.debug(
            "Sending status update",
            session_id=session_id,
            step=step_value,
            message=message,
        )
        return await self.send_json(session_id, payload)

    async def send_complete(
        self,
        session_id: str,
        result: Dict[str, Any],
    ) -> bool:
        """Send the final analysis result to a session.

        Serialises the payload as::

            {
                "type": "complete",
                "step": "complete",
                "result": { ... }
            }

        Parameters
        ----------
        session_id:
            Target session.
        result:
            The full analysis result dict.

        Returns
        -------
        bool
            ``True`` if the message was delivered.
        """
        payload: Dict[str, Any] = {
            "type": "complete",
            "step": AnalysisStep.COMPLETE.value,
            "result": result,
        }
        logger.info("Sending complete message", session_id=session_id)
        return await self.send_json(session_id, payload)

    async def send_error(
        self,
        session_id: str,
        error: str,
        detail: Optional[str] = None,
    ) -> bool:
        """Send an error notification to a session.

        Serialises the payload as::

            {
                "type": "error",
                "step": "error",
                "message": "<error summary>",
                "detail": "<optional traceback or detail>"
            }

        Parameters
        ----------
        session_id:
            Target session.
        error:
            Short error summary.
        detail:
            Optional long-form detail / traceback string.

        Returns
        -------
        bool
            ``True`` if the message was delivered.
        """
        payload: Dict[str, Any] = {
            "type": "error",
            "step": AnalysisStep.ERROR.value,
            "message": error,
        }
        if detail:
            payload["detail"] = detail

        logger.error(
            "Sending error to client",
            session_id=session_id,
            error=error,
        )
        return await self.send_json(session_id, payload)

    async def broadcast(
        self,
        payload: Dict[str, Any],
        exclude: Optional[list[str]] = None,
    ) -> int:
        """Broadcast a payload to all active sessions.

        Parameters
        ----------
        payload:
            JSON-serialisable dict.
        exclude:
            Optional list of session IDs to skip.

        Returns
        -------
        int
            Number of sessions that received the message.
        """
        exclude_set = set(exclude or [])
        sent = 0
        for sid in list(self._connections.keys()):
            if sid not in exclude_set:
                if await self.send_json(sid, payload):
                    sent += 1
        return sent


# ---------------------------------------------------------------------------
# Module-level singleton — imported by websocket_router and agents
# ---------------------------------------------------------------------------

manager: ConnectionManager = ConnectionManager()
