import dotenv
from src.logging_config import setup_logging
from src.conversation.repl import run_conversation

logger = setup_logging()
logger.info("Starting the application...")

dotenv.load_dotenv()

prompt = f"Plan a 3 day trip to Los Angeles, CA"
run_conversation("dev-session", prompt)

logger.info("Application finished.")