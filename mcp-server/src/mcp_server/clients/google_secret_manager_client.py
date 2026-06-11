from google.cloud import secretmanager
import json
import uuid
from src.mcp_server.config import settings


def _create_secret_with_prefix(prefix: str, data: dict) -> str:
    client = secretmanager.SecretManagerServiceClient()

    secret_uuid = str(uuid.uuid4())
    secret_id = f"{prefix}_{secret_uuid}"

    parent = f"projects/{settings.GOOGLE_PROJECT_ID}"
    secret_path = f"{parent}/secrets/{secret_id}"

    client.create_secret(
        request={
            "parent": parent,
            "secret_id": secret_id,
            "secret": {"replication": {"automatic": {}}},
        }
    )

    payload = json.dumps(data).encode("utf-8")

    client.add_secret_version(
        request={
            "parent": secret_path,
            "payload": {"data": payload},
        }
    )

    return secret_uuid


def _load_secret_with_prefix(prefix: str, secret_uuid: str) -> dict:
    client = secretmanager.SecretManagerServiceClient()

    secret_id = f"{prefix}_{secret_uuid}"
    secret_path = (
        f"projects/{settings.GOOGLE_PROJECT_ID}"
        f"/secrets/{secret_id}/versions/latest"
    )

    response = client.access_secret_version(request={"name": secret_path})

    return json.loads(response.payload.data.decode("utf-8"))


def create_calendar_secret(token_data: dict) -> str:
    return _create_secret_with_prefix("CALENDAR", token_data)

def load_calendar_secret(secret_uuid: str) -> dict:
    return _load_secret_with_prefix("CALENDAR", secret_uuid)


def create_waba_secret(token_data: dict) -> str:
    return _create_secret_with_prefix("WABA", token_data)

def load_waba_secret(secret_uuid: str) -> dict:
    return _load_secret_with_prefix("WABA", secret_uuid)