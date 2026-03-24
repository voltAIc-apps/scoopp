import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from jwt import JWT, jwk_from_dict
from jwt.utils import get_int_from_datetime
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import EmailStr
from pydantic.main import BaseModel
import base64

instance = JWT()
security = HTTPBearer(auto_error=False)
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    import logging as _log
    _log.getLogger(__name__).warning(
        "SECRET_KEY not set — using random key (tokens will not survive restarts)")
    import secrets
    SECRET_KEY = secrets.token_urlsafe(32)
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def get_jwk_from_secret(secret: str):
    """Convert a secret string into a JWK object."""
    secret_bytes = secret.encode('utf-8')
    b64_secret = base64.urlsafe_b64encode(secret_bytes).rstrip(b'=').decode('utf-8')
    return jwk_from_dict({"kty": "oct", "k": b64_secret})

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with an expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": get_int_from_datetime(expire)})
    signing_key = get_jwk_from_secret(SECRET_KEY)
    return instance.encode(to_encode, signing_key, alg='HS256')

def _make_token_verifier(required: bool):
    """Factory: return a FastAPI dependency that verifies JWT tokens."""
    def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
        if credentials is None:
            if required:
                raise HTTPException(status_code=401, detail="Authorization required")
            return None
        token = credentials.credentials
        verifying_key = get_jwk_from_secret(SECRET_KEY)
        try:
            payload = instance.decode(token, verifying_key, do_time_check=True, algorithms='HS256')
            return payload
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    return verify_token


def get_token_dependency(config: Dict):
    """Return the token dependency if JWT is enabled, else a function that returns None."""
    if config.get("security", {}).get("jwt_enabled", False):
        return _make_token_verifier(required=True)
    else:
        return lambda: None


def validate_secret_key():
    """Raise if SECRET_KEY env var is not set. Call during startup when JWT is enabled."""
    if not os.environ.get("SECRET_KEY", ""):
        raise RuntimeError("SECRET_KEY environment variable is required when JWT is enabled")


class TokenRequest(BaseModel):
    email: EmailStr


# ── API key auth (X-API-Key header) for research endpoints ───

def verify_api_key(request) -> None:
    """Validate X-API-Key header against API_KEY env var."""
    api_key = request.headers.get("X-API-Key")
    expected = os.environ.get("API_KEY", "")
    if not expected or not api_key or api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")