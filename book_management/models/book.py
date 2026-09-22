from pydantic import BaseModel
from typing import List, Optional


# Base model for Book with relevant fields
class BookBase(BaseModel):
    title: str
    author_id: int
    book_link: str
    genres: List[str]  # List of genre names
    average_rating: Optional[float] = None
    published_year: Optional[int] = None


# Model for creating a new book
class BookCreate(BookBase):
    pass


# Model for the response of a book, which includes both id and all fields
class BookResponse(BookBase):
    id: int


# Model for a book with id, inheriting from BookBase
class Book(BookBase):
    id: int
