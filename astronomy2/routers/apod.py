import sqlite3
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query

from auth.security import get_api_key
from database import get_db_connection
from models.apod import Apod, ApodCreate
from nasa_fetcher import (
    fetch_and_store_apod,
    sync_historical_apods,
    _validate_date,
)


router = APIRouter()


@router.get("/", response_model=Union[List[Apod], Apod])
def list_apod_entries(date: Optional[str] = Query(default=None)):
    """Return all saved APOD entries."""
    conn = get_db_connection()
    try:
        if date is not None:
            try:
                _validate_date(date)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            rows = conn.execute(
                "SELECT * FROM apod_entries WHERE date = ?", (date,)
            ).fetchall()
            if not rows:
                raise HTTPException(status_code=404, detail="Entry not found")
        else:
            rows = conn.execute("SELECT * FROM apod_entries ORDER BY date").fetchall()
        if date is not None:
            return dict(rows[0])
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/{date}", response_model=Apod)
def get_apod_entry(date: str):
    """Return one APOD entry by date."""
    try:
        _validate_date(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM apod_entries WHERE date = ?", (date,)
        ).fetchone()
    finally:
        conn.close()

    if row is not None:
        return dict(row)

    try:
        return fetch_and_store_apod(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/", response_model=Apod, dependencies=[Depends(get_api_key)])
def create_apod_entry(apod: ApodCreate):
    """Create an APOD entry manually."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO apod_entries
                (date, title, explanation, url, hdurl, media_type, copyright)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                apod.date,
                apod.title,
                apod.explanation,
                apod.url,
                apod.hdurl,
                apod.media_type,
                apod.copyright,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM apod_entries WHERE date = ?", (apod.date,)
        ).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Entry already exists")
    finally:
        conn.close()

    return dict(row)


@router.post("/fetch", response_model=Apod, dependencies=[Depends(get_api_key)])
def fetch_apod_entry(date: Optional[str] = None):
    """Fetch an APOD entry from NASA and save it."""
    try:
        return fetch_and_store_apod(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/sync", dependencies=[Depends(get_api_key)])
def sync_apod_entries(start_date: Optional[str] = Query(default=None)):
    """Fill missing APOD entries from today through 2000-01-01."""
    try:
        if start_date is not None:
            _validate_date(start_date)
        return sync_historical_apods(start_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.put("/{id}", response_model=Apod, dependencies=[Depends(get_api_key)])
def update_apod_entry(id: int, apod: ApodCreate):
    """Update an APOD entry by id."""
    conn = get_db_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM apod_entries WHERE id = ?", (id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Entry not found")

        try:
            conn.execute(
                """
                UPDATE apod_entries
                SET date = ?, title = ?, explanation = ?, url = ?, hdurl = ?,
                    media_type = ?, copyright = ?
                WHERE id = ?
                """,
                (
                    apod.date,
                    apod.title,
                    apod.explanation,
                    apod.url,
                    apod.hdurl,
                    apod.media_type,
                    apod.copyright,
                    id,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Entry already exists")

        row = conn.execute(
            "SELECT * FROM apod_entries WHERE id = ?", (id,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


@router.delete("/{id}", dependencies=[Depends(get_api_key)])
def delete_apod_entry(id: int):
    """Delete an APOD entry by id."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("DELETE FROM apod_entries WHERE id = ?", (id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        conn.commit()
    finally:
        conn.close()

    return {"detail": "Entry deleted"}
