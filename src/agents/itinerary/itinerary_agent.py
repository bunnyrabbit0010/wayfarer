import logging
from pathlib import Path
from src.agents.itinerary.loop import run_agent_loop

logger = logging.getLogger(__name__)

def run_itinerary_agent(input_items: list, user_message: str) -> tuple[str, list]:
    """Runs one turn of the itinerary agent. If input_items is empty, loads the system prompt first."""
    if not input_items:
        logger.info("Loading Itinerary Agent System Prompt...")
        prompt_path = Path("src/agents/itinerary/prompt.md")
        system_prompt = prompt_path.read_text(encoding="utf-8")
        input_items.append({"role": "system", "content": system_prompt})

    # Append the user's message to the conversation history
    input_items.append({"role": "user", "content": user_message})

    # Run the agent loop with the updated conversation history
    message, updated_input_items = run_agent_loop(input_items)

    return message, updated_input_items