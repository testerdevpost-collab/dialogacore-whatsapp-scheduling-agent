import logging
from datetime import datetime, timedelta, timezone

from src.mcp_server.services.google_calendar_service import (
    create_event_advanced,
    list_events_full,
    update_event,
    delete_event,
)

from src.mcp_server.clients.valkey_client import (
    memory_commander,
    SessionKeyBuilder
)

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def get_service(context: dict):
    gcal = context["secrets"]["google-calendar"]

    creds = Credentials(
        token=gcal.get("access_token"),
        refresh_token=gcal.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=gcal.get("client_id"),
        client_secret=gcal.get("client_secret"),
        scopes=[gcal.get("scope")],
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        gcal["access_token"] = creds.token
        memory_commander.set(context["__key__"], context, 600)

    return build("calendar", "v3", credentials=creds)


def normalize(e: dict):
    return {
        "id": e["id"],
        "title": e.get("summary"),
        "description": e.get("description"),  # 👈 ESSENCIAL
        "start": e["start"].get("dateTime") or e["start"].get("date"),
        "end": e["end"].get("dateTime") or e["end"].get("date"),
        "status": e.get("status"),
        "creator": e.get("creator", {}).get("email"),
        "extendedProperties": e.get("extendedProperties")
    }


def calendar_list_events(context: dict, input: dict):
    service = get_service(context)

    now = datetime.now(timezone.utc)  
    start = now                     
    end = now + timedelta(days=30)

    events = list_events_full(service, "primary", start, end)
    return [normalize(e) for e in events]


def calendar_create_event(context: dict, input: dict):
    service = get_service(context)

    event_id = input.get("event_id")

    if event_id:
        key = SessionKeyBuilder.idempotency(f"event:{event_id}")

        if not memory_commander.acquire_lock(
            key,
            memory_commander.DEFAULT_EPHEMERAL_IDEM_TTL_SECONDS,
        ):
            return {"status": "duplicate_ignored"}

    event = create_event_advanced(
        service=service,
        calendar_id="primary",
        summary=input["summary"],
        description=input.get("description"),
        start_time=input["start"],
        end_time=input["end"],
        attendees=input.get("attendees"),
        conference=input.get("conference", False),
        extended_properties=input.get("extendedProperties")
    )

    if not event:
        return {"error": "failed_to_create_event"}  # ✅ fix

    return normalize(event)


def calendar_update_event(context: dict, input: dict):
    service = get_service(context)

    current = service.events().get(
        calendarId="primary",
        eventId=input["event_id"]
    ).execute()

    # garantir datas
    start = input.get("start") or current["start"].get("dateTime") or current["start"].get("date")
    end = input.get("end") or current["end"].get("dateTime") or current["end"].get("date")

    # formato esperado
    input["start"] = {"dateTime": start}
    input["end"] = {"dateTime": end}

    # ✨ novos campos opcionais
    if "title" in input:
        input["summary"] = input.pop("title")

    if "description" in input:
        input["description"] = input["description"]

    if "location" in input:
        input["location"] = input["location"]

    updated = update_event(
        service=service,
        calendar_id="primary",
        event_id=input["event_id"],
        update_fields=input
    )

    if not updated:
        return {"error": "failed_to_update_event"}

    return normalize(updated)


def calendar_delete_event(context: dict, input: dict):
    service = get_service(context)

    try:
        delete_event(service, "primary", input["event_id"])
        return {"success": True}
    except Exception:
        return {"error": "failed_to_delete_event"}  


GOOGLE_CALENDAR_TOOLS = {
    "calendar_list_events": calendar_list_events,
    "calendar_create_event": calendar_create_event,
    "calendar_update_event": calendar_update_event,
    "calendar_delete_event": calendar_delete_event,
}