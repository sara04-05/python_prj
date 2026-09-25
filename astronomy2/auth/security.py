import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader


load_dotenv()

API_KEY = os.getenv("API_KEYS")
api_key_header = APIKeyHeader(name="api-key", auto_error=False)


def get_api_key(api_key: str = Depends(api_key_header)):
    """Validate the API key provided in the request header."""
    if not API_KEY or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    return api_key
