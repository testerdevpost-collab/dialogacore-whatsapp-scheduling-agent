from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from jose import jwt, JWTError

from src.mcp_server.config import settings

ALGORITHM = "HS256"

def _get_secret() -> str:
    if not settings.SETUP_TOKEN_SECRET_KEY:
        raise RuntimeError("SETUP_TOKEN_SECRET_KEY não configurada no ambiente!")
    return settings.SETUP_TOKEN_SECRET_KEY


def generate_setup_token(
    *,
    sub: str,
    business_id: str,
    agent_id: str,
    expires_in_minutes: int | None = None,
) -> str:
    """
    Gera um token JWT de uso controlado para fluxo de setup de agente.
    """
    secret = _get_secret()
    now = datetime.now(tz=timezone.utc)

    ttl = expires_in_minutes or settings.SETUP_TOKEN_EXPIRE_MINUTES

    payload = {
        # Rastreabilidade
        "sub": sub,
        "business_id": business_id,
        "agent_id": agent_id,

        # Controle de uso
        "purpose": "agent_setup",

        # Controle temporal
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl)).timestamp()),
    }

    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def verify_setup_token(token: str) -> Dict[str, Any]:
    """
    Valida assinatura, expiração e contrato semântico do token de setup.
    Retorna o payload se estiver válido.
    """
    secret = _get_secret()

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={
                "require": ["exp", "iat", "purpose", "business_id", "agent_id", "sub"]
            },
        )
    except JWTError as e:
        raise ValueError(f"Token inválido ou expirado: {str(e)}")

    # Checagem semântica de propósito
    if payload.get("purpose") != "agent_setup":
        raise ValueError("Token com purpose inválido")

    # Checagem estrutural defensiva
    required_fields = {"sub", "business_id", "agent_id"}
    if not required_fields.issubset(payload.keys()):
        raise ValueError("Token incompleto: campos obrigatórios ausentes")

    return payload
