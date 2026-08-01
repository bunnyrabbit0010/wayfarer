from src.agents.itinerary.itinerary_agent import run_itinerary_agent
from src.state.session_store import SessionState

def handle_turn(state: SessionState, user_message: str) -> str:
    reply, updated_input_items = run_itinerary_agent(state.input_items, user_message)
    state.input_items = updated_input_items
    return reply