import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from dotenv import load_dotenv

from database import get_db_connection

load_dotenv()
router = APIRouter()

VALID_API_KEY = os.getenv("API_KEY")


class ImageCreate(BaseModel):
    title: str
    category_id: int
    image_url: str
    explanation: Optional[str] = ""
    topics: List[str] = []
    capture_date: Optional[str] = ""
    year: int
    rating: float = 0.0


def require_api_key(api_key: str = Header(...)):
    if api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")


@router.get("/")
def get_images():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM images").fetchall()
    conn.close()
    images = []
    for row in rows:
        image = dict(row)
        image['topics'] = [t.strip() for t in (image['topics'] or "").split(',') if t.strip()]
        images.append(image)
    return images


@router.post("/")
def add_image(image: ImageCreate, api_key: str = Header(...)):
    require_api_key(api_key)
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO images (title, category_id, image_url, explanation, topics, capture_date, year, rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        image.title, image.category_id, image.image_url, image.explanation,
        ', '.join(image.topics), image.capture_date, image.year, image.rating
    ))
    conn.commit()
    conn.close()
    return {"message": f"Image '{image.title}' added."}


@router.put("/{image_id}")
def update_image(image_id: int, image: ImageCreate, api_key: str = Header(...)):
    require_api_key(api_key)
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Image not found.")
    conn.execute('''
        UPDATE images
        SET title = ?, category_id = ?, image_url = ?, explanation = ?,
            topics = ?, capture_date = ?, year = ?, rating = ?
        WHERE id = ?
    ''', (
        image.title, image.category_id, image.image_url, image.explanation,
        ', '.join(image.topics), image.capture_date, image.year, image.rating, image_id
    ))
    conn.commit()
    conn.close()
    return {"message": f"Image '{image.title}' updated."}


@router.delete("/{image_id}")
def delete_image(image_id: int, api_key: str = Header(...)):
    require_api_key(api_key)
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Image not found.")
    conn.execute("DELETE FROM images WHERE id = ?", (image_id,))
    conn.commit()
    conn.close()
    return {"message": "Image deleted."}
