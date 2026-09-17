import os

from fastapi import APIRouter, Header, HTTPException
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

VALID_API_KEY = os.getenv("API_KEY")


@router.get("/")
def validate_key(api_key: str = Header(...)):
    if not VALID_API_KEY:
        raise HTTPException(status_code=500, detail="Server API_KEY is not configured.")
    if api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return {"valid": True}
