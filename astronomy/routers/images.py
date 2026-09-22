import sqlite3
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from models.image import Image, ImageCreate
from database import get_db_connection
from auth.security import get_api_key

router = APIRouter()


@router.get("/", response_model=List[Image])
def get_images():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, category_id, image_url, explanation, topics, capture_date, year, rating FROM images")
    images = cursor.fetchall()
    conn.close()

    return [
        {
            "id": image[0],
            "title": image[1],
            "category_id": image[2],
            "image_url": image[3],
            "explanation": image[4],
            "topics": [t.strip() for t in (image[5] or "").split(',') if t.strip()],
            "capture_date": image[6],
            "year": image[7],
            "rating": image[8]
        }
        for image in images
    ]


@router.post("/", response_model=Image)
def create_image(image: ImageCreate, _: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        topics_str = ", ".join(image.topics) if image.topics else ""
        cursor.execute('''
            INSERT INTO images (title, category_id, image_url, explanation, topics, capture_date, year, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (image.title, image.category_id, image.image_url, image.explanation,
              topics_str, image.capture_date, image.year, image.rating))
        conn.commit()
        image_id = cursor.lastrowid
        return Image(id=image_id, **image.dict())
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The image '{image.title}' already exists."
        )
    finally:
        conn.close()


@router.put("/{image_id}", response_model=Image)
def update_image(image_id: int, image: ImageCreate, _: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()
    topics_str = ", ".join(image.topics) if image.topics else ""
    cursor.execute(
        '''UPDATE images
           SET title = ?, category_id = ?, image_url = ?, explanation = ?,
               topics = ?, capture_date = ?, year = ?, rating = ?
           WHERE id = ?''',
        (image.title, image.category_id, image.image_url, image.explanation,
         topics_str, image.capture_date, image.year, image.rating, image_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Image not found")
    conn.commit()
    conn.close()
    return Image(id=image_id, **image.dict())


@router.delete("/{image_id}", response_model=dict)
def delete_image(image_id: int, _: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Image not found")
    conn.commit()
    conn.close()

    return {"detail": "Image deleted"}
