import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Literal
import requests
import uuid

from fastapi.middleware.cors import CORSMiddleware 
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, UUID4, Field

from src.mcp_server.clients.google_pubsub_client import pubsub_publisher
from src.mcp_server.clients.google_secret_manager_client import create_calendar_secret
from src.mcp_server.config import settings
from src.mcp_server.security.setup_token import verify_setup_token


# ================== ROUTER ==================

router = APIRouter()

# ==============================================================================
# PAYLOAD DE DADOS DO EVENTO
# ==============================================================================

class GoogleCalendarData(BaseModel):
    secret_uuid: str = Field(..., description="UUID do secret criado no Secret Manager")
    provider: str = Field("google-calendar", description="Provedor da integração")


# ==============================================================================
# EVENTO FINAL
# ==============================================================================

class McpGoogleCalendarSetupEvent(BaseModel):
    event_id: str
    event_type: Literal["mcp_google_calendar_submitted"] = "mcp_google_calendar_submitted"
    version: str = Field("1.0", description="Versão do Schema")
    sub: str
    business_id: UUID4
    agent_id: UUID4
    data: GoogleCalendarData
    timestamp: datetime


# ================== AUTH LINK ==================

@router.get("/google-calendar/auth_link")
async def get_auth_link(token: str = Query(..., description="Token JWT de setup")):
    try:
        claims = verify_setup_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    agent_id = claims["agent_id"]
    business_id = claims["business_id"]
    sub = claims["sub"]

    params = {
        "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
        "response_type": "code",
        "scope": settings.GOOGLE_CALENDAR_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": token,
    }

    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    #return {"auth_url": url}
    return RedirectResponse(
        url=url,
        status_code=307
    )


# ================== CALLBACK ==================

@router.get("/google-calendar/oauth/callback")
async def oauth2callback(request: Request):
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    token = request.query_params.get("state")

    if error or not code or not token:
        return RedirectResponse(settings.URL_GOOGLE_CALENDAR_ERROR)

    try:
        claims = verify_setup_token(token)
    except Exception:
        return RedirectResponse(settings.URL_GOOGLE_CALENDAR_ERROR)

    agent_id = claims["agent_id"]
    business_id = claims["business_id"]
    sub = claims["sub"]

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
        "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    r = requests.post(token_url, data=data)
    if r.status_code != 200:
        return RedirectResponse(settings.URL_GOOGLE_CALENDAR_ERROR)

    token_response = r.json()
    token_response["client_id"] = settings.GOOGLE_CALENDAR_CLIENT_ID
    token_response["client_secret"] = settings.GOOGLE_CALENDAR_CLIENT_SECRET
    token_response["token_uri"] = "https://oauth2.googleapis.com/token"

    secret_uuid = create_calendar_secret(token_response)

    event = McpGoogleCalendarSetupEvent(
        event_id=str(uuid.uuid4()),
        sub=sub,
        business_id=business_id,
        agent_id=agent_id,
        timestamp=datetime.now(timezone.utc),
        data=GoogleCalendarData(
            secret_uuid=secret_uuid,
            provider="google-calendar"
        )
    )

    message_json = event.model_dump(mode="json")

    pubsub_publisher.publish_message_sync(
        topic_id=settings.PUBSUB_SETUP_EVENTS_TOPIC,
        message=message_json,
        attributes={
            "event_type": event.event_type,
            "version": event.version,
            "business_id": str(event.business_id),
            "source": "mcp-google-calendar"
        }
    )

    # Redireciona para um página em dialogacore.com
    #return RedirectResponse("https://dialogacore.com/google-calendar-success")
    return HTMLResponse("""
        <script>
        window.opener.postMessage({ type: "google_connected" }, "*");
        window.close();
        </script>
        """)
