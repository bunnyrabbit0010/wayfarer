import logging
logger = logging.getLogger(__name__)

import openai
import json
import dotenv
from src.agent.tools import tools, tool_mapping


dotenv.load_dotenv()

def run_agent_loop(input_items: list) -> tuple[str, list]:
    """
    Main loop for the agent that interacts with the OpenAI API.
    It sends user prompts, handles function calls, and processes responses.
    """
    logger.debug("Starting the agent loop...")
    client  = openai.OpenAI()

    logger.debug("Calling OpenAI API to get an interesting fact...")

    while True:
        openai_response = client.responses.create(
            model="gpt-4o-mini",
            input=input_items,
            tools=tools,
        )

        if openai_response.status != "completed":
            raise Exception(f"OpenAI API call failed with status: {openai_response.status}")

        # Preserve every output item, including program and reasoning items.
        input_items.extend(item.model_dump(exclude_none=True) for item in openai_response.output)

        for item in openai_response.output:
            if item.type == "message":
                return item.content[0].text, input_items
            elif item.type == "function_call":
                fn_name = item.name
                fn_args = json.loads(item.arguments)
                logger.info(f"Function call detected: {fn_name} with arguments: {fn_args}")
                fn_response = tool_mapping.get(fn_name)(**fn_args)
                logger.info(f"Function response: {fn_response}")

                input_items.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(fn_response)
                })
                continue
            else:
                logger.warning(f"Unexpected output type: {item.type}")
        
