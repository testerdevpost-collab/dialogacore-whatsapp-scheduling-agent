# Módulo de Conectividade e Operações com Valkey
#
# Este módulo serve como o ponto de acesso centralizado para todas as interações
# com o armazenamento de memória da aplicação utilizando Valkey.
#
# Arquitetura:
# 1. Uma factory `get_valkey_client` responsável por instanciar o cliente Valkey
#    de acordo com o modo de operação configurado por variáveis de ambiente.
# 2. Uma classe de abstração `ValkeyCommander` que encapsula as operações de
#    CRUD e a lógica de serialização (JSON), fornecendo uma API de alto nível
#    para o resto da aplicação.
# 3. Uma instância singleton `memory_commander` é exportada para garantir que
#    uma única configuração e pool de conexões sejam usados em toda a aplicação.

import os
import json
import time
import logging
from typing import Dict, Any, Optional

import redis
import google.auth
import google.auth.transport.requests

from ..config import settings

logger = logging.getLogger(__name__)

def wait_for_valkey_connection(
    retry_interval_seconds: int = 10,
    max_retries: Optional[int] = None
) -> redis.Redis:
    """
    Tenta conectar ao Valkey até obter sucesso (ou até atingir max_retries).

    Em caso de falha, emite logs e aguarda antes de tentar novamente.
    """
    attempt = 0

    while True:
        try:
            attempt += 1
            logger.info(f"Attempting to connect to Valkey (attempt {attempt})...")
            client = get_valkey_client()
            logger.info("Valkey connection established successfully.")
            return client

        except Exception as e:
            logger.error(
                "Valkey is unavailable. "
                f"Retrying in {retry_interval_seconds}s. "
                f"Error: {e}",
                exc_info=True
            )

            if max_retries is not None and attempt >= max_retries:
                logger.critical("Maximum number of retries reached. Giving up.")
                raise

            time.sleep(retry_interval_seconds)


# --- Seção 1: Factory de Conexão ---

def _get_managed_client() -> redis.Redis:
    """
    Cria um cliente para uma instância Valkey gerenciada acessível diretamente
    via host e porta.

    Este modo não utiliza autenticação IAM nem TLS, assumindo que o controle
    de acesso e a segurança da rede são tratados externamente.

    Returns:
        Uma instância do cliente redis.Redis conectada.

    Raises:
        redis.exceptions.ConnectionError: Se a conexão com o endpoint falhar.
    """
    host = settings.MANAGED_VALKEY_HOST
    port = int(settings.MANAGED_VALKEY_PORT)
    logger.info(f"MANAGED MODE: Connecting to Valkey endpoint at {host}:{port}.")
    try:
        client = redis.Redis(host=host, port=port, decode_responses=True)
        client.ping()
        logger.info("Connection to managed Valkey established successfully.")
        return client
    except redis.exceptions.ConnectionError as e:
        logger.critical(
            f"MANAGED CONNECTION FAILED: Could not connect to Valkey at {host}:{port}. "
            f"Error: {e}"
        )
        raise

def _get_secure_gcp_client() -> redis.Redis:
    """
    Cria um cliente Valkey utilizando autenticação IAM e conexão segura (TLS).

    Este modo assume que o endpoint de conexão (host e porta) é fornecido
    pelas variáveis MANAGED_VALKEY_HOST e MANAGED_VALKEY_PORT, mesmo quando
    executado em ambiente GCP. O uso de IAM/TLS é controlado apenas pelo
    modo de conexão, não pelo endpoint.

    Returns:
        Uma instância do cliente redis.Redis conectada e autenticada.

    Raises:
        ValueError: Se host ou porta não estiverem configurados.
        google.auth.exceptions.DefaultCredentialsError: Se as credenciais do GCP não puderem ser obtidas.
        redis.exceptions.AuthenticationError: Se a autenticação IAM falhar.
        redis.exceptions.ConnectionError: Se houver falha de conectividade.
    """
    host = settings.MANAGED_VALKEY_HOST
    port = settings.MANAGED_VALKEY_PORT

    if not host or not port:
        logger.critical(
            "GCP CONFIGURATION ERROR: MANAGED_VALKEY_HOST ou MANAGED_VALKEY_PORT não definidos."
        )
        raise ValueError("Configuração de Valkey incompleta para modo seguro.")

    port = int(port)
    logger.info(f"GCP MODE: Initiating secure connection to Valkey endpoint at {host}:{port}.")

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    access_token = credentials.token
    logger.debug("GCP IAM credentials obtained and access token generated.")

    client = redis.Redis(
        host=host,
        port=port,
        password=access_token,
        ssl=True,
        ssl_cert_reqs="required",
        decode_responses=True
    )

    client.ping()
    logger.info("Secure connection to Valkey established successfully.")
    return client

def get_valkey_client() -> redis.Redis:
    """
    Factory responsável por selecionar o cliente Valkey apropriado.

    A decisão é baseada na variável de ambiente `MANAGED_VALKEY`.
    Quando definida como "true", utiliza um cliente gerenciado direto.
    Caso contrário, assume uma execução no GCP e estabelece conexão segura.

    Returns:
        A instância do cliente redis.Redis apropriada para o ambiente.
    """
    if settings.MANAGED_VALKEY == "true":
        return _get_managed_client()
    else:
        return _get_secure_gcp_client()


# --- Seção 2: Camada de Abstração de Comandos ---
class SessionKeyBuilder:

    @staticmethod
    def session(sender_id: str, agent_id: str) -> str:
        return f"{settings.KEY_PREFIX}:session:{sender_id}:{agent_id}"

    @staticmethod
    def idempotency(sub: str) -> str:
        return f"{settings.KEY_PREFIX}:idempotency:{sub}"

    @staticmethod
    def ephemeral(sub: str):
        return f"{settings.KEY_PREFIX}:ephemeral:{sub}"
    
    @staticmethod
    def ephemeral_config(sub: str):
        return f"{settings.KEY_PREFIX}:ephemeral-config:{sub}"
    
    @staticmethod
    def message_lock(message_id: str) -> str:
        return f"{settings.KEY_PREFIX}:msg:{message_id}"
    

class ValkeyCommander:

    def __init__(self, client: redis.Redis):
        self._client = client
        self.DEFAULT_SESSION_TTL_SECONDS = 21600 # 6Hrs
        self.DEFAULT_SESSION_IDEM_TTL_SECONDS = 10800 # 3hrs
        self.DEFAULT_EPHEMERAL_IDEM_TTL_SECONDS = 600  # 10min
        self.DEFAULT_EPHEMERAL_CONFIG_TTL_SECONDS = 10800  # 3min

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        data = self._client.get(key)
        return json.loads(data) if data else None

    def set(self, key: str, value: Dict[str, Any], ttl: int):
        self._client.set(
            key,
            json.dumps(value),
            ex=ttl
        )

    def delete(self, key: str):
        self._client.delete(key)

    def acquire_lock(self, key: str, ttl: int) -> bool:
        return bool(
            self._client.set(
                name=key,
                value="PROCESSING",
                nx=True,
                ex=ttl
            )
        )

# --- Seção 3: Instanciação Singleton Resiliente ---

try:
    _underlying_client = wait_for_valkey_connection(
        retry_interval_seconds=10
    )

    memory_commander = ValkeyCommander(_underlying_client)
    logger.info("Valkey Commander initialized successfully.")

except Exception:
    logger.critical(
        "FATAL: Valkey module initialization failed after retries. "
        "Application cannot proceed."
    )
    memory_commander = None