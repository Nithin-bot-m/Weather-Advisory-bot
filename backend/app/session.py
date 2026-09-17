"""
In-memory session manager for Weather Advisory Support Bot.
Stores conversation history per session_id.
"""
from typing import Dict, List, Any


class SessionManager:
    """
    Lightweight in-memory session manager.
    Maintains independent conversation history per session ID.
    """

    def __init__(self):
        self._sessions: Dict[str, List[Dict[str, Any]]] = {}

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Return the conversation message history for a given session ID."""
        if not session_id:
            return []
        return list(self._sessions.get(session_id, []))

    def add_user_message(self, session_id: str, content: str) -> None:
        """Append a user message to the session history."""
        if not session_id:
            return
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({"role": "user", "content": content})

    def add_assistant_message(self, session_id: str, content: str) -> None:
        """Append an assistant response to the session history."""
        if not session_id:
            return
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({"role": "assistant", "content": content})

    def reset_session(self, session_id: str) -> bool:
        """Remove conversation history for a given session ID."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def clear_all(self) -> None:
        """Clear all active sessions (useful for testing)."""
        self._sessions.clear()


# Global session manager instance
session_manager = SessionManager()
