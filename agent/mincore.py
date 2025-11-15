"""The minimal inner core of an agent

This module automatically handles the function preparation, execution, and
result formatting which makes up the inner core of an agent.

Current functionality and limitations:
- Only supports OpenAI Responses API, not the Completions API.
- Only supports function calling, not custom tools
- Minimal error handling

This is just for illustration and learning, not for production use.

If you want a minimal kit, use the `Agent` class and `function_tool` decorator
from the openai-agents package instead:

- https://github.com/openai/openai-agents
- https://github.com/openai/openai-agents-python?tab=readme-ov-file#functions-example
"""

import functools
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from function_schema import get_function_schema
from openai import OpenAI


logger = logging.getLogger("mincore")


# ----------------------------------------------------------------------------------------------------------------------
#  Function calling helpers
# ----------------------------------------------------------------------------------------------------------------------


@functools.lru_cache(maxsize=10)
def _generate_function_schemas(function_list: List[Callable]) -> List[Dict[str, Any]]:
    """Generate the list of function schemas for the given function list

    This is auto-converted to JSON by the OpenAI client, and is the format which
    is expected by the OpenAI Responses API tools parameter.
    """
    logger.debug(f"Generating function schemas for {len(function_list)} functions")
    function_schemas = []
    for function in function_list:
        schema = get_function_schema(function)
        schema["type"] = "function"
        function_schemas.append(schema)
    logger.debug(f"Function schemas: {function_schemas}")
    return function_schemas


@functools.lru_cache(maxsize=10)
def _generate_function_map(function_list: List[Callable]) -> Dict[str, Callable]:
    """Generate a dictionary of function names to functions

    This is used to map the function names in the OpenAI Responses API responses to the actual functions.
    """
    logger.debug(f"Generating function map for {len(function_list)} functions")
    function_map = {}
    for function in function_list:
        function_map[function.__name__] = function
    return function_map


def _extract_function_calls(response: Any) -> List[Dict[str, Any]]:
    """Extract function calls from an OpenAI Responses API response

    Partial response example:
    Response(id='resp_689642afba24819db78b5844701f90b40d951c6324caaef1',
        created_at=1754677935.0,
        error=None,
        incomplete_details=None,
        instructions=None,
        metadata={},
        model='gpt-5-2025-08-07',
        object='response',
        output=[
        ResponseReasoningItem(id='rs_689642b2aca4819d89363bef35abe5990d951c6324caaef1',
                                summary=[],
                                type='reasoning',
                                content=None,
                                encrypted_content=None,
                                status=None),
        ResponseFunctionToolCall(arguments='{"hour":8,"minute":0}',
                                    call_id='call_O2FXP3fxvB9daHWSmOGCItou',
                                    name='some_function_name',
                                    type='function_call',
                                    id='fc_689642bed090819db88a71d872a5a28a0d951c6324caaef1',
                                    status='completed')
        ],
        parallel_tool_calls=True,
        temperature=1.0,

    """
    calls: List[Dict[str, Any]] = []

    output = getattr(response, "output", None)
    if not isinstance(output, list):
        return calls

    for item in output:
        # Duck-typing ResponseFunctionToolCall: requires name and arguments
        name = getattr(item, "name", None)
        arguments = getattr(item, "arguments", None)
        if not name or arguments is None:
            continue

        call_id = getattr(item, "call_id", None) or getattr(item, "id", "")

        if isinstance(arguments, str):
            try:
                args = json.loads(arguments)
            except Exception:
                args = {}
        elif isinstance(arguments, dict):
            args = arguments
        else:
            args = {}

        calls.append({"id": str(call_id) if call_id is not None else "", "name": str(name), "args": args})

    return calls


# ----------------------------------------------------------------------------------------------------------------------
#  LLM interaction class
# ----------------------------------------------------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = """
You are a helpful assistant.
"""


class MinCore:
    """The inner core of an agent

    This class handles the LLM interactions with function calling using the OpenAI Responses API
    """

    def __init__(self, api_key: str, model: str = "gpt-5-nano", system_prompt: str = DEFAULT_SYSTEM_PROMPT):
        """Initialize the client

        Args:
            api_key: The OpenAI API key to use
            model: The model to use (default: "gpt-5")
            system_prompt: The system prompt to use (default: DEFAULT_SYSTEM_PROMPT)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt

    def _create_conversation(self) -> str:
        """Create a new conversation with the given system prompt

        Returns:
            str: The response ID that can be used for future messages
        """
        # Create initial response with system prompt
        response = self.client.responses.create(
            model=self.model,
            input=[{"role": "system", "content": self.system_prompt}],
        )
        return response.id

    def send_message(
        self,
        user_message: str,
        previous_response_id: Optional[str] = None,
        functions: Tuple[Callable[..., Any], ...] = (),
        max_function_rounds: int = 5,
    ) -> Tuple[str, str]:
        """Send a message with function calling using the Responses API

        Args:
            user_message: The next user message to send
            previous_response_id: The ID from a previous response to continue that conversation (None for new conversation)
            functions: List of functions available to the LLM
            max_function_rounds: Maximum number of function calling rounds (default 5)

        Returns:
            Tuple[str, str]: The new response ID and text
        """
        # Bootstrap the conversation
        if previous_response_id is None:
            logger.info("Bootstrapping conversation")
            previous_response_id = self._create_conversation()

        # Prepare the function schemas and map
        function_schemas = None
        function_map = None
        if functions:
            logger.debug("Functions provided, generating function schemas and map")
            function_schemas = _generate_function_schemas(functions)
            function_map = _generate_function_map(functions)

        # Send the next user message with functions available
        logger.info("Sending user message with functions to LLM")
        user_input = [{"role": "user", "content": user_message}]
        response = self.client.responses.create(
            model=self.model,
            previous_response_id=previous_response_id,
            input=user_input,
            tools=function_schemas,
        )
        logger.debug("Initial message with functions sent to LLM")

        # ------------------------------------------------------------------------------------------
        # Function calling loop
        # ------------------------------------------------------------------------------------------
        # If requested by the LLM, call functions iteratively up to the maximum number of rounds
        for _ in range(max_function_rounds):
            # Extract any function calls from the response
            function_calls = _extract_function_calls(response)
            if not function_calls:
                logger.debug("No function calls found in response, stopping function calling loop")
                break

            # Execute the requested functions and capture the results
            function_call_results: List[Dict[str, str]] = []
            for call in function_calls:
                name = call["name"]
                args = call["args"]
                call_id = call["id"]

                try:
                    logger.info(f"Executing function: {name} with args: {args}")
                    if name not in function_map:
                        raise ValueError(f"Unknown function: {name}")
                    result = function_map[name](**args)
                    logger.info(f"Function: {name} executed with result: {result}")
                except Exception as e:
                    logger.error(f"Function: {name} execution failed: {e}")
                    result = {"error": str(e)}

                # Convert result to string for API input
                output_str = json.dumps(result, default=str) if isinstance(result, (dict, list)) else str(result)
                function_call_results.append({"call_id": call_id, "output": output_str})

            # Format the function call results to be used as input for the next request
            function_call_results_formatted = [
                {"type": "function_call_output", "call_id": result["call_id"], "output": result["output"]} for result in function_call_results
            ]

            # Continue the conversation with function results
            response = self.client.responses.create(
                model=self.model,
                previous_response_id=response.id,
                input=function_call_results_formatted,
            )
        # ------------------------------------------------------------------------------------------
        # End of function calling loop
        # ------------------------------------------------------------------------------------------

        # Return the latest response ID and response text
        return response.id, response.output_text
