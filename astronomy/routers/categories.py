import sqlite3
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from models.category import Category, CategoryCreate
from database import get_db_connection
from auth.security import get_api_key

router = APIRouter()


@router.get("/", response_model=List[Category])
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories")
    categories = cursor.fetchall()
    conn.close()
    return [{"id": category[0], "name": category[1]} for category in categories]


@router.post("/", response_model=Category)
def create_category(
        category: CategoryCreate,
        _: str = Depends(get_api_key)  # Enforce API key
):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category.name,))
        conn.commit()
        category_id = cursor.lastrowid
        return Category(id=category_id, name=category.name)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The category '{category.name}' already exists."
        )
    finally:
        conn.close()


@router.put("/{category_id}", response_model=Category)
def update_category(
        category_id: int,
        category: CategoryCreate,
        _: str = Depends(get_api_key)  # Enforce API key
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE categories SET name = ? WHERE id = ?", (category.name, category_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Category not found")
    conn.commit()
    conn.close()
    return Category(id=category_id, name=category.name)


@router.delete("/{category_id}", response_model=dict)
def delete_category(
        category_id: int,
        _: str = Depends(get_api_key)  # Enforce API key
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Category not found")
    conn.commit()
    conn.close()

    return {"detail": "Category deleted"}
