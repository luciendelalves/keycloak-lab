import json
from functools import lru_cache
from typing import Set, Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from pydantic import BaseModel

# ==== Ajuste aqui se mudar o realm/issuer ====
ISSUER = "http://localhost:8080/realms/lab-iam"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"

ALGORITHMS = ["RS256"]  # Keycloak padrão
security = HTTPBearer(auto_error=True)

class TokenData(BaseModel):
    sub: str
    roles: Set[str]

@lru_cache(maxsize=1)
def _fetch_jwks() -> dict:
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(JWKS_URL)
        resp.raise_for_status()
        return resp.json()

def _get_key(token: str) -> dict:
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    jwks = _fetch_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: key not found")

def decode_token(token: str) -> dict:
    key = _get_key(token)
    try:
        # Ignoramos 'aud' (client público) — valida iss/exp/iats etc.
        payload = jwt.decode(
            token,
            key,
            algorithms=ALGORITHMS,
            options={"verify_aud": False},
            issuer=ISSUER,
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

def extract_realm_roles(payload: dict) -> Set[str]:
    roles = set()
    realm_access = payload.get("realm_access") or {}
    roles_list = realm_access.get("roles") or []
    for r in roles_list:
        if isinstance(r, str):
            roles.add(r)
    return roles

def get_current_roles(creds: HTTPAuthorizationCredentials = Depends(security)) -> Set[str]:
    if not creds or not creds.scheme.lower() == "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    payload = decode_token(creds.credentials)
    roles = extract_realm_roles(payload)
    if not roles:
        # Sem roles = não autorizado para rotas protegidas
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: no roles")
    return roles
