from pydantic import BaseModel


# Base model for Author with only the name field
class AuthorBase(BaseModel):
    name: str


# Model for creating a new author, which includes only the name
class AuthorCreate(AuthorBase):
    pass


# Model for the response of an author, which includes both id and name
class AuthorResponse(BaseModel):
    id: int
    name: str


# Model for an author with id, inheriting from AuthorBase
class Author(AuthorBase):
    id: int
