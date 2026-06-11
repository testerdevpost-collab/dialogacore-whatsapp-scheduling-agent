from fastapi import FastAPI

from .api.v1.google_calendar_auth import router as google_router
from .api.v1.meta_waba_auth import router as meta_router
from .mcp.api.v1.mcp import router as mcp_router


app = FastAPI(title="MCP Server")

# ================== HEALTH ==================

@app.get("/health")
async def health():
    return {"status": "ok"}


# ================== ROUTERS ==================
app.include_router(google_router, prefix="/api/v1")
#app.include_router(meta_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/mcp/v1")