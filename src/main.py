
from src.logging_config import setup_logging
from src.agent.conversation import run_conversation

logger = setup_logging()
logger.info("Starting the application...")

prompt = f"Tell me interesting facts about Mexico"
run_conversation(prompt)

logger.info("Application finished.")