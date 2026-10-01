from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ApodBase(BaseModel):
    date: str
    title: str = Field(min_length=1)
    explanation: str
    url: str = Field(min_length=1)
    hdurl: Optional[str] = None
    media_type: str
    copyright: Optional[str] = None


class ApodCreate(ApodBase):
    @field_validator("date")
    @classmethod
    def date_must_be_iso(cls, value):
        try:
            parsed = date_type.fromisoformat(value)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format.")
        if parsed.isoformat() != value:
            raise ValueError("Date must be in YYYY-MM-DD format.")
        return value

    @field_validator("media_type")
    @classmethod
    def media_type_must_be_known(cls, value):
        if value not in {"image", "video", "other"}:
            raise ValueError("Media type must be image, video or other.")
        return value


class Apod(ApodBase):
    id: int
