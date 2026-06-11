import json
import logging
from typing import Dict, Any
from google.cloud import pubsub_v1
from src.mcp_server.config import settings

logger = logging.getLogger(__name__)

class PubSubPublisher:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        try:
            self.publisher = pubsub_v1.PublisherClient()
            self.project_id = settings.GOOGLE_PROJECT_ID
            logger.info(f"PubSub inicializado. Projeto: {self.project_id}")
        except Exception as e:
            logger.critical(f"Falha ao iniciar PubSub: {e}")
            raise

    def publish_message_sync(self, topic_id: str, message: Dict[str, Any], attributes: Dict[str, str] = None) -> str:
        """
        Publica e aguarda confirmação (block/await) para garantir que não houve perda de dados.
        """
        topic_path = self.publisher.topic_path(self.project_id, topic_id)
        data = json.dumps(message).encode("utf-8")
        attrs = {k: str(v) for k, v in (attributes or {}).items()}

        try:
            # O future.result() bloqueia até o PubSub confirmar o recebimento
            future = self.publisher.publish(topic_path, data, **attrs)
            msg_id = future.result(timeout=10) # Timeout de 10s para não travar a thread indefinidamente
            logger.info(f"Evento publicado no tópico {topic_id}: {msg_id}")
            return msg_id
        except Exception as e:
            logger.error(f"Erro ao publicar no PubSub: {e}")
            raise RuntimeError(f"PubSub Publish Failed: {e}")

pubsub_publisher = PubSubPublisher()