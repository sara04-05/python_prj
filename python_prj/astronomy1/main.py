from contextlib import asynccontextmanager

from fastapi import FastAPI

import database
from routers import apod, api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.create_database()
    yield


app = FastAPI(title="Astronomy Picture of the Day API", lifespan=lifespan)

app.include_router(apod.router, prefix="/api/apod", tags=["APOD"])
app.include_router(api_key.router, prefix="/api/validate_key", tags=["Auth"])
