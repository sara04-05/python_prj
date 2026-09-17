from fastapi import FastAPI
from routers import authors, books, api_key
from database import create_database

# Initialize FastAPI app
app = FastAPI(
    title="Book Management System",
    description="An API for managing books, authors, and genres.",
    version="1.0.0",
)

# Include the routers
app.include_router(authors.router, prefix="/api/authors", tags=["Authors"])
app.include_router(books.router, prefix="/api/books", tags=["Books"])
app.include_router(api_key.router, prefix="/api/validate_key")


@app.on_event("startup")
def startup():
    # Initialize the database tables
    create_database()
