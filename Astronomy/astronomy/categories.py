import os

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from dotenv import load_dotenv

from database import get_db_connection

load_dotenv()
router = APIRouter()

VALID_API_KEY = os.getenv("API_KEY")


class CategoryCreate(BaseModel):
    name: str


def require_api_key(api_key: str = Header(...)):
    if api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")


@router.get("/")
def get_categories():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.post("/")
def add_category(category: CategoryCreate, api_key: str = Header(...)):
    require_api_key(api_key)
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO categories (name) VALUES (?)", (category.name,))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"message": f"Category '{category.name}' added."}


@router.put("/{category_id}")
def update_category(category_id: int, category: CategoryCreate, api_key: str = Header(...)):
    require_api_key(api_key)
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Category not found.")
    conn.execute("UPDATE categories SET name = ? WHERE id = ?", (category.name, category_id))
    conn.commit()
    conn.close()
    return {"message": f"Category updated to '{category.name}'."}


@router.delete("/{category_id}")
def delete_category(category_id: int, api_key: str = Header(...)):
    require_api_key(api_key)
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Category not found.")
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
    return {"message": "Category deleted."}
