from fastapi import FastAPI
from routers import categories, images, api_key
from database import create_database

# Initialize FastAPI app
app = FastAPI(
    title="APOD Personal Gallery",
    description="An API for archiving and rating NASA's Astronomy Picture of the Day.",
    version="1.0.0",
)

# Include the routers
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(images.router, prefix="/api/images", tags=["Images"])
app.include_router(api_key.router, prefix="/api/validate_key")


@app.on_event("startup")
def startup():
    # Initialize the database tables
    create_database()
