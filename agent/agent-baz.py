#!/usr/bin/env python
"""A prototype mini agent

This prototype illustrates basic function calling with the OpenAI Responses API.
"""

import os
import random

from dotenv import load_dotenv

from mincore import MinCore


SYSTEM_PROMPT = """
You are a helpful assistant named Baz.
You have two tools to return a random color or return a random number.
You can only discuss the color and number tools, or make polite conversation.
"""


def get_color() -> str:
    """Select and return a random color"""
    colors = ["red", "green", "blue", "yellow", "purple", "orange", "brown", "black", "white"]
    return random.choice(colors)


def get_number() -> int:
    """Select and return a random number integer"""
    return random.randint(0, 100)


def agent_loop():
    """Main loop for the agent"""
    import logging

    logging.basicConfig(level=logging.INFO)
    # logging.basicConfig(level=logging.DEBUG)

    # Load the API key from the env file or environment variables
    load_dotenv(dotenv_path=".env")
    api_key = os.getenv("BAZ_OPENAI_API_KEY")
    if not api_key:
        raise ValueError("BAZ_OPENAI_API_KEY not found in environment variables")

    # Initialize the agent core
    llm = MinCore(api_key=api_key, system_prompt=SYSTEM_PROMPT)

    # Main interaction loop
    response_id = None
    funcs = (get_color, get_number)
    while True:
        user_input = input("\n>>> You: ")
        print("")
        response_id, response_text = llm.send_message(user_input, previous_response_id=response_id, functions=funcs)
        print("\n>>> Agent: ", response_text)


if __name__ == "__main__":
    agent_loop()
