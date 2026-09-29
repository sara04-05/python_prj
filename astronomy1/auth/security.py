import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

api_key_header = APIKeyHeader(name="api-key", auto_error=False)


def get_valid_api_keys():
    """Return the configured API keys (API_KEYS may hold a comma-separated list)."""
    raw_keys = os.getenv("API_KEYS", "")
    return [key.strip() for key in raw_keys.split(",") if key.strip()]


def get_api_key(api_key: str = Depends(api_key_header)):
    """Validate the API key provided in the request header."""
    if not api_key or not any(
        secrets.compare_digest(api_key.encode(), valid_key.encode())
        for valid_key in get_valid_api_keys()
    ):
        raise HTTPException(status_code=401, detail="Invalid API Key")

    return api_key
