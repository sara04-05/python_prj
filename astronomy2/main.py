from fastapi import FastAPI

import database
from routers import apod, api_key


app = FastAPI(title="Astronomy Picture of the Day API")

app.include_router(apod.router, prefix="/api/apod", tags=["APOD"])
app.include_router(api_key.router, prefix="/api/validate_key")


@app.on_event("startup")
def startup():
    database.create_database()
