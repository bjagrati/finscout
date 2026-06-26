"""Reusable helpers for calling Claude with structured output via tool use."""
import os
from pathlib import Path
from typing import Type, TypeVar

from dotenv import load_dotenv
from anthropic import Anthropic
from pydantic import BaseModel


_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_ENV_PATH)

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

_client = Anthropic(api_key=api_key)
DEFAULT_MODEL = "claude-sonnet-4-6"

T = TypeVar("T", bound=BaseModel)


def structured_call(
    prompt: str,
    response_model: Type[T],
    system: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4000,
) -> T:
    """Call Claude and get a Pydantic-validated structured response."""
    schema = response_model.model_json_schema()
    tool_name = _pydantic_to_tool_name(response_model)
    tools = [
        {
            "name": tool_name,
            "description": response_model.__doc__ or "Return the structured response.",
            "input_schema": schema,
        }
    ]
    
    response = _client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=tools,
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": prompt}],
    )
    
    for block in response.content:
        if block.type == "tool_use":
            return response_model(**block.input)
    
    raise ValueError(
        f"Expected a tool_use response, but got: {[b.type for b in response.content]}"
    )


def _pydantic_to_tool_name(model_class: Type[BaseModel]) -> str:
    name = model_class.__name__
    result = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            result.append("_")
        result.append(ch.lower())
    return "".join(result)