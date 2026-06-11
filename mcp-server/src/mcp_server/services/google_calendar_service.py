# ======================================================================
# ARQUIVO: google_calendar.py
# RESPONSABILIDADE: Lógica de negócio para API Google Calendar
# ======================================================================

import uuid
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.mcp_server.clients.google_secret_manager_client import load_calendar_secret

# ======================================================================
# SCOPES
# ======================================================================

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events"
]

# ======================================================================
# SERVICE BUILDER
# ======================================================================

def get_google_calendar_service(secret_uuid: str):
    """
    Cria o service do Google Calendar usando token salvo no Secret Manager
    """

    # 🔐 Carrega JSON do secret
    token_data = load_calendar_secret(secret_uuid)

    # 🧠 Cria credenciais
    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=SCOPES,
    )

    # 🔁 Se expirou, renova automaticamente (SÓ EM MEMÓRIA)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # 🏗️ Cria o service
    service = build("calendar", "v3", credentials=creds)
    return service

# ======================================================================
# FUNÇÕES BÁSICAS
# ======================================================================

def create_event(service, calendar_id: str, event_body: dict):
    try:
        created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return created_event
    except Exception as error:
        print(f"Erro ao criar evento: {error}")
        return None


def list_events(service, calendar_id: str, time_min: datetime, time_max: datetime, max_results=10):
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        return events_result.get("items", [])
    except HttpError as error:
        print(f"Erro ao listar eventos: {error}")
        return []


def update_event(service, calendar_id: str, event_id: str, update_fields: dict):
    try:
        original_event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        original_event.update(update_fields)

        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=original_event
        ).execute()

        return updated_event
    except HttpError as error:
        print(f"Erro ao alterar evento: {error}")
        return None


def delete_event(service, calendar_id: str, event_id: str):
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except HttpError as error:
        print(f"Erro ao deletar evento: {error}")
        return False

# ======================================================================
# FUNÇÕES AVANÇADAS
# ======================================================================

def create_event_advanced(
    service,
    calendar_id: str,
    summary: str,
    description: str,
    start_time: str,
    end_time: str,
    location: str = None,
    attendees: list = None,
    reminders: dict = None,
    recurrence: list = None,
    conference: bool = False,
    extended_properties: dict = None 
):
    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
    }

    if location:
        event_body["location"] = location
    if attendees:
        event_body["attendees"] = [{"email": a} for a in attendees]
    if reminders:
        event_body["reminders"] = reminders
    if recurrence:
        event_body["recurrence"] = recurrence
    if conference:
        event_body["conferenceData"] = {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"}
            }
        }
    if extended_properties:
        event_body["extendedProperties"] = extended_properties
        
    try:
        kwargs = {}
        if conference:
            kwargs["conferenceDataVersion"] = 1

        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            **kwargs
        ).execute()

        return created_event

    except HttpError as error:
        print(f"Erro ao criar evento: {error}")
        return None


def search_events(service, calendar_id: str, query: str, time_min: datetime, time_max: datetime, max_results=10, show_deleted=False):
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            q=query,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
            showDeleted=show_deleted
        ).execute()

        return events_result.get("items", [])

    except HttpError as error:
        print(f"Erro ao buscar eventos: {error}")
        return []


def move_event(service, calendar_id_from: str, calendar_id_to: str, event_id: str):
    try:
        moved_event = service.events().move(
            calendarId=calendar_id_from,
            eventId=event_id,
            destination=calendar_id_to
        ).execute()

        return moved_event

    except HttpError as error:
        print(f"Erro ao mover evento: {error}")
        return None


def cancel_event(service, calendar_id: str, event_id: str):
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except HttpError as error:
        print(f"Erro ao cancelar evento: {error}")
        return False


def get_freebusy(service, calendar_id: str, time_min: datetime, time_max: datetime):
    try:
        body = {
            "timeMin": time_min.isoformat() + "Z",
            "timeMax": time_max.isoformat() + "Z",
            "items": [{"id": calendar_id}]
        }

        freebusy_result = service.freebusy().query(body=body).execute()
        return freebusy_result["calendars"][calendar_id]["busy"]

    except HttpError as error:
        print(f"Erro ao consultar Freebusy: {error}")
        return None


def list_events_with_status(service, calendar_id: str, time_min: datetime, time_max: datetime, status: str = "confirmed", max_results=10):
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
            showDeleted=(status == "cancelled")
        ).execute()

        return [
            e for e in events_result.get("items", [])
            if e.get("status", "confirmed") == status
        ]

    except HttpError as error:
        print(f"Erro ao listar eventos por status: {error}")
        return []

def list_events_full(service, calendar_id, time_min, time_max):
    events = []
    page_token = None

    while True:
        response = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token
        ).execute()

        events.extend(response.get("items", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return events