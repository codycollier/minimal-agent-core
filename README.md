# minimal-agent-core

An illustration of the small inner core of a function calling agent


## Overview

This project is for illustration and learning. It is a simple agent which can
hold a conversation and provide a random color and/or number.

The core of an agent is relatively simple, and consists of a loop around special
calls to an LLM where you send both a user message and a list of tools. The LLM
decides when it needs to call a function, tells the program. The program makes
the function call(s) and sends the result(s) back to the LLM to continue the
conversation.

You can do all this in just a few hundred lines of code, most of which is about
handling the representation of the functions and calls as json. This specific 
implementation uses the OpenAPI Responses API.

Contents:

* `agent-baz.py` - System prompt, functions / tools, and a simple input loop
* `mincore.py` - OpenAI wrapper class which handles all the function translation work


## Try it out

```
# virtual environment (using uv)
> uv venv
> source .venv/bin/activate
> uv pip install -r requirements.txt

# configure an openai api key
echo 'BAZ_OPENAI_API_KEY="abc-123"' > .env

# run
> python ./agent/agent-baz.py
```


## Example run

```
$python ./agent/agent-baz.py

>>> You: Hey!

INFO:mincore:Bootstrapping conversation
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 200 OK"
INFO:mincore:Sending user message with functions to LLM
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 200 OK"

>>> Agent:  Hey there! How can I help today? I can generate:
- a random color
- a random number
- or both

If you want a number, tell me the min and max. Or I can just give you a color and a number (1-100) right now—your call.

>>> You: Can I get a color please

INFO:mincore:Sending user message with functions to LLM
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 200 OK"
INFO:mincore:Executing function: get_color with args: {}
INFO:mincore:Function: get_color executed with result: red
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 200 OK"

>>> Agent:  Here's a random color: red.

Would you like another color, or a random number as well (tell me a min and max if you want a specific range)?

>>> You: A number now

INFO:mincore:Sending user message with functions to LLM
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 200 OK"
INFO:mincore:Executing function: get_number with args: {}
INFO:mincore:Function: get_number executed with result: 20
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 200 OK"

>>> Agent:  Here's a random number: 20.

Would you like another number (maybe with a specific range), or should I give you another color as well?

>>> You: How about two colors and a number?

INFO:mincore:Sending user message with functions to LLM
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 200 OK"
INFO:mincore:Executing function: get_color with args: {}
INFO:mincore:Function: get_color executed with result: blue
INFO:mincore:Executing function: get_color with args: {}
INFO:mincore:Function: get_color executed with result: orange
INFO:mincore:Executing function: get_number with args: {}
INFO:mincore:Function: get_number executed with result: 27
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 200 OK"

>>> Agent:  Here you go:
- Color 1: blue
- Color 2: orange
- Number: 27

Want me to generate another set, or specify a range for the number?

>>> You: ^C
```

## Note

If you want a good minimal kit for real development, try the `Agent` class and
the `function_tool` decorator from the openai-agents package:

* https://github.com/openai/openai-agents
* https://github.com/openai/openai-agents-python?tab=readme-ov-file#functions-example

