from pydantic import BaseModel


# Base model for Category with only the name field
class CategoryBase(BaseModel):
    name: str


# Model for creating a new category
class CategoryCreate(CategoryBase):
    pass


# Model for the response of a category, which includes both id and name
class CategoryResponse(BaseModel):
    id: int
    name: str


# Model for a category with id, inheriting from CategoryBase
class Category(CategoryBase):
    id: int
