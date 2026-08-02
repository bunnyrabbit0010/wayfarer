from __future__ import annotations
from src.models.itinerary import Itinerary


class SessionState:
    input_items: list   # conversation history sent to/from the LLM
    itinerary: Itinerary | None  # the itinerary object, if generated

    def __init__(self):
        self.input_items = []   
        self.itinerary = None

_session_store = {}

def get_session(session_id) -> SessionState:
    """
    Retrieves the session state for a given session ID.
    If the session does not exist, it creates a new one.

    Args:
        session_id (str): The unique identifier for the session.    
    """
    if session_id not in _session_store:
        _session_store[session_id] = SessionState()
    return _session_store[session_id]   

def save_session(session_id, state) -> None:
    """
    Saves the session state for a given session ID.

    Args:
        session_id (str): The unique identifier for the session.
        state (SessionState): The session state to be saved.
    """
    _session_store[session_id] = state
