
from src.logging_config import setup_logging

logger = setup_logging()
setup_logging()

logger.info("Starting the application...")

from src.agent.loop import run_agent_loop


prompt = f"""
What's the capital and official languages of India, sourced from a reliable database?
"""
response =  run_agent_loop(prompt)
print(f"Response from the agent: {response}")
