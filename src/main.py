
from src.logging_config import setup_logging
from src.agent.conversation import run_conversation

logger = setup_logging()
logger.info("Starting the application...")

prompt = f"I will be traveling to San Jose California next week. Can you suggest an Indian restaurant in the area that is highly rated and has good reviews? Please provide the name, address, and a brief description of the restaurant.   "
run_conversation(prompt)

logger.info("Application finished.")