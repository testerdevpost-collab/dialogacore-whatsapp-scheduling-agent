import os
import logging
from dotenv import load_dotenv
import json

load_dotenv()
logger = logging.getLogger(__name__)


class Settings:
    def __init__(self):
        # App
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        
        # VALKEY| MEMORYSTORE 
        self.MANAGED_VALKEY = os.getenv('MANAGED_VALKEY')
        self.MANAGED_VALKEY_HOST = os.getenv('MANAGED_VALKEY_HOST')
        self.MANAGED_VALKEY_PORT = os.getenv('MANAGED_VALKEY_PORT')
        self.KEY_PREFIX = f"mcp-server:{self.ENVIRONMENT}"

        # GCP (Simples getenv, se não tiver, fica None)
        self.GOOGLE_OAUTH_CREDENTIALS = json.loads(
            os.getenv("DIALOGACORE_DEV_GOOGLE_OAUTH_CREDENTIALS", "{}")
        )
        self.GOOGLE_CALENDAR_CLIENT_ID = self.GOOGLE_OAUTH_CREDENTIALS.get("web", {}).get("client_id")
        self.GOOGLE_CALENDAR_CLIENT_SECRET = self.GOOGLE_OAUTH_CREDENTIALS.get("web", {}).get("client_secret")
        self.GOOGLE_CALENDAR_REDIRECT_URI = self.GOOGLE_OAUTH_CREDENTIALS.get("web", {}).get("redirect_uris", [None])[0]

        # SCOPE
        self.GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"

        self.GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
        self.URL_GOOGLE_CALENDAR_ERROR = os.getenv("URL_GOOGLE_CALENDAR_ERROR")
        self.PUBSUB_SETUP_EVENTS_TOPIC= os.getenv("PUBSUB_SETUP_EVENTS_TOPIC")
        self.SETUP_TOKEN_SECRET_KEY = os.getenv("SETUP_TOKEN_SECRET_KEY")

        # META
        self.WHATSAPP_META_APP_ID = os.getenv("WHATSAPP_META_APP_ID")
        self.WHATSAPP_META_APP_SECRET = os.getenv("WHATSAPP_META_APP_SECRET")
        self.WHATSAPP_META_REDIRECT_URI = os.getenv("WHATSAPP_META_REDIRECT_URI")
        self.WHATSAPP_META_CONFIG_ID = os.getenv("WHATSAPP_META_CONFIG_ID")
        self.WHATSAPP_META_WABA_PIN = os.getenv("WHATSAPP_META_WABA_PIN")
        self.URL_WHATSAPP_META_ERROR = os.getenv("URL_WHATSAPP_META_ERROR")
    
# Instância global simples
settings = Settings()
