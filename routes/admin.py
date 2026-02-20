import base64
import os

from fastapi import APIRouter, Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from config import settings

router = APIRouter(prefix="/admin", tags=["admin"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def verify_key(key: str = Security(api_key_header)) -> None:
    if key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


class CookiesBody(BaseModel):
    cookies_base64: str


@router.post("/cookies")
async def refresh_cookies(body: CookiesBody, _=Security(verify_key)) -> dict:
    """Update cookies.txt at runtime without redeploying."""
    try:
        raw = base64.b64decode(body.cookies_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64")

    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    path = os.path.join(settings.TEMP_DIR, "cookies.txt")
    with open(path, "wb") as f:
        f.write(raw)
    settings.COOKIES_FILE = path
    return {"status": "ok", "path": path, "size": len(raw)}


@router.delete("/cookies")
async def clear_cookies(_=Security(verify_key)) -> dict:
    """Remove cookies to fall back to cookieless extraction."""
    if settings.COOKIES_FILE and os.path.exists(settings.COOKIES_FILE):
        os.remove(settings.COOKIES_FILE)
    settings.COOKIES_FILE = ""
    return {"status": "ok", "message": "Cookies cleared"}
