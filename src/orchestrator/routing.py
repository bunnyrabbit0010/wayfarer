from src.agents.itinerary.itinerary_agent import run_itinerary_agent
from src.agents.itinerary.loop import AgentResultType
from src.state.session_store import SessionState


def handle_turn(state: SessionState, user_message: str) -> str:
    result_type, payload, updated_input_items = run_itinerary_agent(state.input_items, user_message)
    state.input_items = updated_input_items

    if result_type == AgentResultType.ITINERARY:
        state.itinerary = payload
        return "Glad we now have an Itinerary to work with.. what do you want to do next.."
    
    return payload  # only correct for the MESSAGE case