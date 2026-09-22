from pydantic import BaseModel
from typing import List, Optional


# Base model for Image with relevant fields
class ImageBase(BaseModel):
    title: str
    category_id: int
    image_url: str
    explanation: Optional[str] = ""
    topics: List[str] = []
    capture_date: Optional[str] = ""
    year: int
    rating: float = 0.0


# Model for creating a new image
class ImageCreate(ImageBase):
    pass


# Model for the response of an image, which includes both id and all fields
class ImageResponse(ImageBase):
    id: int


# Model for an image with id, inheriting from ImageBase
class Image(ImageBase):
    id: int
