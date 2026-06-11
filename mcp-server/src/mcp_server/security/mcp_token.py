from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from jose import jwt, JWTError

from ..config import settings


ALGORITHM = "HS256"


def _get_secret() -> str:
    if not settings.SETUP_TOKEN_SECRET_KEY:
        raise RuntimeError("SETUP_TOKEN_SECRET_KEY não configurada no ambiente!")
    return settings.SETUP_TOKEN_SECRET_KEY


# =========================================================
# GENERATE MCP TOKEN
# =========================================================

def generate_mcp_token(
    *,
    session_context: str,
    expires_in_minutes: int | None = None,
) -> str:
    """
    Gera token JWT para execução de tools do MCP.
    """

    secret = _get_secret()
    now = datetime.now(tz=timezone.utc)

    ttl = expires_in_minutes or settings.MCP_TOKEN_EXPIRE_MINUTES

    payload = {
        "sub": session_context,
        "purpose": "mcp_functions",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl)).timestamp()),
    }

    return jwt.encode(payload, secret, algorithm=ALGORITHM)


# =========================================================
# VERIFY MCP TOKEN
# =========================================================

def verify_mcp_token(token: str) -> Dict[str, Any]:
    """
    Valida assinatura, expiração e contrato do token MCP.
    Retorna payload válido.
    """

    secret = _get_secret()

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={
                "require": ["exp", "iat", "purpose", "sub"]
            },
        )
    except JWTError as e:
        raise ValueError(f"Token inválido ou expirado: {str(e)}")

    # valida purpose
    if payload.get("purpose") != "mcp_functions":
        raise ValueError("Token com purpose inválido")

    # valida sub (context key)
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise ValueError("Token inválido: sub ausente ou inválido")

    return payload