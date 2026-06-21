"""JWT auth + RBAC dependency helpers."""
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from .config import get_settings

S = get_settings()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def hash_password(p: str) -> str: return pwd.hash(p)
def verify_password(p: str, h: str) -> bool: return pwd.verify(p, h)

def create_token(sub: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=S.jwt_expire_min)
    return jwt.encode({"sub": sub, "role": role, "exp": exp}, S.jwt_secret, algorithm=S.jwt_alg)

def current_user(token: Annotated[str, Depends(oauth2)]) -> dict:
    try:
        payload = jwt.decode(token, S.jwt_secret, algorithms=[S.jwt_alg])
        return {"id": payload["sub"], "role": payload["role"]}
    except (JWTError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")

def require_role(*roles: str):
    def dep(user: Annotated[dict, Depends(current_user)]) -> dict:
        if user["role"] not in roles and user["role"] != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return user
    return dep
