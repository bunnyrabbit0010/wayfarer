import logging
logger = logging.getLogger(__name__)

from src.agent.loop import run_agent_loop
from pathlib import Path

def run_conversation(prompt: str):
    """
    Runs a conversation with the agent using the provided prompt.

    Args:
        prompt (str): The initial prompt to start the conversation.

    Returns:
        str: The final response from the agent.
    """
    logger.info("Loading System Prompt...")

    prompt_path = Path("src/prompts/system_prompt.txt")
    system_prompt = prompt_path.read_text(encoding="utf-8")

    input_items = [
        { "role": "system",  "content": system_prompt},
        { "role": "user", "content": prompt }
    ]

    while True:
        message, updated_input_items = run_agent_loop(input_items)
        logger.info(f"Agent response: {message}")

        next_prompt = input("What's your next message? (or type 'exit' to quit): ")
        if next_prompt.lower() == 'exit':
            logger.info("Thank you for using the agent. Exiting the conversation.")
            return 

        input_items = updated_input_items
        input_items.append({
            "role": "user",
            "content": next_prompt
        })
    
