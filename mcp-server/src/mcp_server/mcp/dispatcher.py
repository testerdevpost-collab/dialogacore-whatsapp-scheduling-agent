from .registry import TOOLS
from ..security.mcp_token import verify_mcp_token
from ..clients.valkey_client import memory_commander


def resolve_context(token: str):
    payload = verify_mcp_token(token)

    key = payload["sub"]

    context = memory_commander.get(key)
    if not context:
        raise Exception("Context expired")

    context["__key__"] = key
    return context


def handle_tool_call(tool_name: str, input: dict, token: str):
    context = resolve_context(token)

    tool = TOOLS.get(tool_name)
    if not tool:
        raise Exception("Tool not found")

    return tool(context, input)