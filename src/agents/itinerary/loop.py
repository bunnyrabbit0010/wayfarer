from __future__ import annotations
from enum import Enum
import logging
import openai
import json
from src.agents.itinerary.tools import tools, tool_mapping
from src.models.itinerary import Itinerary
from src.tools.validators import check_itinerary_feasibility

logger = logging.getLogger(__name__)

MAX_ITR_RETRIES = 3  # Maximum number of retries for itinerary validation

class AgentResultType(str, Enum):
    MESSAGE = "message"
    ITINERARY = "itinerary"

def _append_function_output(input_items: list, call_id: str, output: dict) -> None:
    input_items.append({
        "type": "function_call_output",
        "call_id": call_id,
        "output": json.dumps(output),
    })

def run_agent_loop(input_items: list) -> tuple[AgentResultType, str | Itinerary, list]:

    """
    Main loop for the agent that interacts with the OpenAI API.
    It sends user prompts, handles function calls, and processes responses.
    """
    logger.debug("Starting the agent loop...")

    itinerary_retries = 0
    client  = openai.OpenAI()

    logger.debug("Calling OpenAI API ...")

    while True:
        openai_response = client.responses.create(
            model="gpt-4o",
            input=input_items,
            tools=tools,
        )

        if openai_response.status != "completed":
            raise Exception(f"OpenAI API call failed with status: {openai_response.status}")

        input_items.extend(item.model_dump(exclude_none=True) for item in openai_response.output)

        pending_message = None      # holds a message's text, if this response had one
        terminal_result = None      # (AgentResultType, payload), set if a function_call ends the turn

        for item in openai_response.output:
            if item.type == "message":
                pending_message = item.content[0].text

            elif item.type == "function_call":
                fn_name = item.name
                fn_args = json.loads(item.arguments)
                logger.debug(f"Function call detected: {fn_name} with arguments: {fn_args}")
                fn_response = tool_mapping.get(fn_name)(**fn_args)
                logger.debug(f"Function response: {fn_response}")

                if fn_name == "submit_itinerary":
                    errors = check_itinerary_feasibility(fn_response)
                    _append_function_output(input_items, item.call_id, {"errors": errors})

                    if errors:
                        itinerary_retries += 1
                        logger.warning(f"Itinerary validation failed with errors: {errors}. Retrying ({itinerary_retries}/{MAX_ITR_RETRIES})...")
                        if itinerary_retries >= MAX_ITR_RETRIES:
                            terminal_result = (AgentResultType.MESSAGE, (
                                "I couldn't quite finalize a fully feasible itinerary — " + "; ".join(errors)
                            ))
                    else:
                        terminal_result = (AgentResultType.ITINERARY, fn_response)
                else:
                    _append_function_output(input_items, item.call_id, fn_response)

            elif item.type == "web_search_call":
                logger.debug(f"Web search call detected: {item.model_dump(exclude_none=True)}")
            else:
                logger.warning(f"Unexpected output type: {item.type}")

        # Only now, after every function_call in this batch has been answered,
        # decide what this turn actually resolves to.
        if terminal_result is not None:
            return terminal_result[0], terminal_result[1], input_items
        if pending_message is not None:
            return AgentResultType.MESSAGE, pending_message, input_items
        # Otherwise: only non-terminal tool calls happened (e.g. get_places) — loop again automatically.