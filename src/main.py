import dotenv
from src.logging_config import setup_logging
from src.conversation.repl import run_conversation

logger = setup_logging()
logger.info("Starting the application...")

dotenv.load_dotenv()

prompt = f"Plan a 10 day trip to Italy. Must include Rome. Optionally include Venice/Florence/Lake Cuomo/Cinque Terre. Trip is between November 18th and the 29th. "
run_conversation("dev-session", prompt)

logger.info("Application finished.")