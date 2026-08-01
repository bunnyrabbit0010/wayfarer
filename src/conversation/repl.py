from src.orchestrator.routing import handle_turn
from src.state.session_store import get_session, save_session


def run_conversation(session_id: str, prompt: str):
    state = get_session(session_id)
    while True:
        reply = handle_turn(state, prompt)
        save_session(session_id, state)
        print(f"Agent response: {reply}")
        next_prompt = input("What's your next message? (or type 'exit' to quit): ")
        if next_prompt.lower() == 'exit':
            return
        prompt = next_prompt