import os
import time
from typing import Dict, Any, Set, Optional

import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, JWTError

# ========= Config =========
ISSUER = os.getenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/lab-iam")
DISCOVERY_URL = f"{ISSUER}/.well-known/openid-configuration"
ALGS = ["RS256", "PS256"]  # Keycloak geralmente usa RS256

# ========= Cache simples de JWKS =========
JWKS_URI: Optional[str] = None
JWKS: Dict[str, Any] = {}
JWKS_FETCHED_AT: float = 0.0
JWKS_TTL_SECONDS = 600  # 10 minutos


async def fetch_oidc_and_jwks(force: bool = False):
    """Busca o discovery e o JWKS e guarda em cache."""
    global JWKS_URI, JWKS, JWKS_FETCHED_AT

    now = time.time()
    if not force and JWKS and (now - JWKS_FETCHED_AT) < JWKS_TTL_SECONDS and JWKS_URI:
        return

    async with httpx.AsyncClient(timeout=10) as client:
        # Descoberta OIDC
        r = await client.get(DISCOVERY_URL)
        r.raise_for_status()
        data = r.json()
        JWKS_URI = data["jwks_uri"]

        # JWKS
        r2 = await client.get(JWKS_URI)
        r2.raise_for_status()
        JWKS = r2.json()
        JWKS_FETCHED_AT = now


def find_jwk_for_token(token: str) -> Dict[str, Any]:
    """Seleciona a chave pública pelo 'kid' do token."""
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    if not kid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_kid")

    for key in JWKS.get("keys", []):
        if key.get("kid") == kid:
            return key

    # Se não achou, força refresh do JWKS (chave rotacionada)
    return {}


async def decode_and_validate(token: str) -> Dict[str, Any]:
    """Valida assinatura, exp e issuer. 'aud' é ignorado por ser client public."""
    await fetch_oidc_and_jwks()
    jwk = find_jwk_for_token(token)
    if not jwk:
        # tenta refetch
        await fetch_oidc_and_jwks(force=True)
        jwk = find_jwk_for_token(token)
        if not jwk:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="jwk_not_found_for_kid")

    try:
        payload = jwt.decode(
            token,
            jwk,  # python-jose aceita JWK dict
            algorithms=ALGS,
            issuer=ISSUER,
            options={"verify_aud": False},  # 'aud' pode não conter 'lab-api' em client public
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"invalid_token: {str(e)}")


async def get_current_user(authorization: str = Header(None)) -> Dict[str, Any]:
    """Extrai o Bearer token do header Authorization e valida."""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_authorization_header")

    scheme, param = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer" or not param:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_authorization_scheme")

    payload = await decode_and_validate(param)

    # Realm roles vêm em payload["realm_access"]["roles"]
    roles = set(payload.get("realm_access", {}).get("roles", []))
    payload["_roles"] = roles
    return payload


def require_roles(allowed: Set[str]):
    async def _checker(user: Dict[str, Any] = Depends(get_current_user)):
        roles: Set[str] = user.get("_roles", set())
        if roles.intersection(allowed):
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_role")

    return _checker


# ========= FastAPI =========
app = FastAPI(title="service-a (FastAPI + Keycloak OIDC)")

@app.on_event("startup")
async def _startup():
    # Precarrega JWKS para falhar rápido se ISSUER estiver errado
    try:
        await fetch_oidc_and_jwks(force=True)
    except Exception:
        # Não derruba a API; erros serão mostrados no primeiro request protegido
        pass


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/reports")
async def reports(_user=Depends(require_roles({"analyst", "admin"}))):
    # Conteúdo de exemplo
    return {"reports": [{"id": 1, "name": "Monthly KPIs"}, {"id": 2, "name": "Security Events"}]}


@app.get("/admin")
async def admin(_user=Depends(require_roles({"admin"}))):
    return {"admin": "secret-panel"}
