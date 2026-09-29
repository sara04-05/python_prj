from fastapi import APIRouter, Depends

from auth.security import get_api_key


router = APIRouter()


@router.get("/", dependencies=[Depends(get_api_key)])
def validate_api_key():
    """Validate the API key provided in the request header."""
    return {"message": "API Key is valid"}
