from fastapi import APIRouter, Header

from ...dispatcher import handle_tool_call

router = APIRouter()

@router.post("/tools/call")
async def call_tool(body: dict, authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")

    return handle_tool_call(
        tool_name=body["tool"],
        input=body.get("input", {}),
        token=token
    )