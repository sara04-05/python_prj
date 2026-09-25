from typing import Optional

from pydantic import BaseModel


class ApodBase(BaseModel):
    date: str
    title: str
    explanation: str
    url: str
    hdurl: Optional[str] = None
    media_type: str
    copyright: Optional[str] = None


class ApodCreate(ApodBase):
    pass


class Apod(ApodBase):
    id: int
