import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.express as px
from dotenv import load_dotenv
import os

load_dotenv()
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000/api')

api_key_input = st.text_input("Enter API Key", type="password")


def validate_api_key(api_key):
    headers = {"api-key": api_key}
    response = requests.get(f"{BASE_URL}/validate_key/", headers=headers)
    return response.status_code == 200


# ---------- Categories ----------
def get_categories():
    response = requests.get(f"{BASE_URL}/categories/")
    if response.status_code == 200:
        return response.json()
    st.error("Failed to fetch categories.")
    return []


def add_category(api_key, name):
    headers = {"api-key": api_key}
    response = requests.post(f"{BASE_URL}/categories/", json={"name": name}, headers=headers)
    if response.status_code == 200:
        st.success(f"Category '{name}' added successfully!")
    else:
        st.error(f"Failed to add category: {response.json().get('detail', 'Unknown error')}")


def update_category(api_key, category_id, name):
    headers = {"api-key": api_key}
    response = requests.put(f"{BASE_URL}/categories/{category_id}", json={"name": name}, headers=headers)
    if response.status_code == 200:
        st.success(f"Category updated to '{name}'!")
    else:
        st.error(f"Failed to update category: {response.json().get('detail', 'Unknown error')}")


def delete_category(api_key, category_id):
    headers = {"api-key": api_key}
    response = requests.delete(f"{BASE_URL}/categories/{category_id}", headers=headers)
    if response.status_code == 200:
        st.success("Category deleted successfully!")
    else:
        st.error(f"Failed to delete category: {response.json().get('detail', 'Unknown error')}")


# ---------- Images ----------
def get_images():
    response = requests.get(f"{BASE_URL}/images/")
    if response.status_code == 200:
        return response.json()
    st.error("Failed to fetch images.")
    return []


def add_image(api_key, image_data):
    headers = {"api-key": api_key}
    response = requests.post(f"{BASE_URL}/images/", json=image_data, headers=headers)
    if response.status_code == 200:
        st.success(f"Image '{image_data['title']}' added successfully!")
    else:
        st.error(f"Failed to add image: {response.json().get('detail', 'Unknown error')}")


def update_image(api_key, image_id, image_data):
    headers = {"api-key": api_key}
    response = requests.put(f"{BASE_URL}/images/{image_id}", json=image_data, headers=headers)
    if response.status_code == 200:
        st.success(f"Image '{image_data['title']}' updated successfully!")
    else:
        st.error(f"Failed to update image: {response.json().get('detail', 'Unknown error')}")


def delete_image(api_key, image_id):
    headers = {"api-key": api_key}
    response = requests.delete(f"{BASE_URL}/images/{image_id}", headers=headers)
    if response.status_code == 200:
        st.success("Image deleted successfully!")
    else:
        st.error(f"Failed to delete image: {response.json().get('detail', 'Unknown error')}")


# ---------- Categories Dashboard ----------
def categories_dashboard(api_key):
    st.title("Categories Management")

    st.subheader("Existing Categories")
    categories = get_categories()
    df_categories = pd.DataFrame(categories)
    st.dataframe(df_categories, use_container_width=True)

    st.subheader("Add New Category")
    new_category_name = st.text_input("Category Name")
    if st.button("Add Category"):
        if new_category_name.strip():
            add_category(api_key, new_category_name)
        else:
            st.error("Category name cannot be empty.")

    action = st.radio("What would you like to do?", options=["Update Category", "Delete Category"])

    if action == "Update Category":
        selected = st.selectbox("Select Category to Update", options=[c['name'] for c in categories])
        new_name = st.text_input("New Category Name", value=selected)
        if st.button("Update Category"):
            category_id = next((c['id'] for c in categories if c['name'] == selected), None)
            update_category(api_key, category_id, new_name)

    elif action == "Delete Category":
        to_delete = st.selectbox("Select Category to Delete", options=[c['name'] for c in categories])
        if st.button("Delete Category"):
            category_id = next((c['id'] for c in categories if c['name'] == to_delete), None)
            delete_category(api_key, category_id)


# ---------- Images Dashboard ----------
def images_dashboard(api_key):
    st.title("Images Management")

    st.subheader("Existing Images")
    images = get_images()
    categories = get_categories()

    category_id_to_name = {c['id']: c['name'] for c in categories}
    table_rows = []
    for img in images:
        row = dict(img)
        row['category'] = category_id_to_name.get(row['category_id'], 'Unknown')
        row['topics'] = ', '.join(row['topics'])
        del row['category_id']
        table_rows.append(row)

    df_images = pd.DataFrame(table_rows)
    display_cols = [c for c in ['id', 'title', 'category', 'topics', 'rating', 'year', 'capture_date']
                     if c in df_images.columns]
    st.dataframe(df_images[display_cols] if not df_images.empty else df_images, use_container_width=True)

    st.subheader("Add New Image")
    new_title = st.text_input("Title")
    selected_category_name = st.selectbox("Select Category", options=[c['name'] for c in categories],
                                          key="select_category_add")
    new_image_url = st.text_input("Image URL")
    new_topics = st.text_input("Topics (comma-separated)")
    new_rating = st.number_input("Your Rating", min_value=0.0, max_value=5.0, step=0.5)
    new_year = st.number_input("Year", min_value=1995, max_value=datetime.now().year, step=1)
    new_capture_date = st.text_input("Capture Date (YYYY-MM-DD)")
    new_explanation = st.text_area("Explanation")

    if st.button("Add Image"):
        if new_title.strip() and new_image_url.strip():
            topics_list = [t.strip() for t in new_topics.split(',') if t.strip()]
            selected_category_id = next((c['id'] for c in categories if c['name'] == selected_category_name), None)
            image_data = {
                "title": new_title,
                "category_id": selected_category_id,
                "image_url": new_image_url,
                "explanation": new_explanation,
                "topics": topics_list,
                "capture_date": new_capture_date,
                "year": new_year,
                "rating": new_rating
            }
            add_image(api_key, image_data)
        else:
            st.error("Title and Image URL cannot be empty.")

    action = st.radio("What would you like to do?", options=["Update Image", "Delete Image"], key="radio_action")

    if action == "Update Image" and images:
        selected_title = st.selectbox("Select Image to Update", options=[img['title'] for img in images],
                                      key="select_image_update")
        img = next((i for i in images if i['title'] == selected_title), None)
        if img:
            title = st.text_input("Title", value=img['title'], key="upd_title")
            cat_name = category_id_to_name.get(img['category_id'], categories[0]['name'] if categories else "")
            cat_names = [c['name'] for c in categories]
            selected_category_name = st.selectbox(
                "Select Category", options=cat_names,
                index=cat_names.index(cat_name) if cat_name in cat_names else 0,
                key="select_category_update"
            )
            image_url = st.text_input("Image URL", value=img['image_url'], key="upd_url")
            topics = st.text_input("Topics (comma-separated)", value=', '.join(img['topics']), key="upd_topics")
            rating = st.number_input("Your Rating", min_value=0.0, max_value=5.0, step=0.5,
                                     value=float(img['rating']), key="upd_rating")
            year = st.number_input("Year", min_value=1995, max_value=datetime.now().year, step=1,
                                   value=img['year'], key="upd_year")
            capture_date = st.text_input("Capture Date", value=img.get('capture_date', ''), key="upd_date")
            explanation = st.text_area("Explanation", value=img.get('explanation', ''), key="upd_expl")

            if st.button("Update Image"):
                image_data = {
                    "title": title,
                    "category_id": next((c['id'] for c in categories if c['name'] == selected_category_name), None),
                    "image_url": image_url,
                    "explanation": explanation,
                    "topics": [t.strip() for t in topics.split(',') if t.strip()],
                    "capture_date": capture_date,
                    "year": year,
                    "rating": rating
                }
                update_image(api_key, img['id'], image_data)

    elif action == "Delete Image" and images:
        to_delete = st.selectbox("Select Image to Delete", options=[img['title'] for img in images],
                                 key="select_image_delete")
        if st.button("Delete Image"):
            image_id = next((i['id'] for i in images if i['title'] == to_delete), None)
            delete_image(api_key, image_id)


# ---------- Visualizations + Gallery Dashboard ----------
def visualizations_dashboard():
    st.title("Gallery & Visualizations")

    images = get_images()
    categories = get_categories()

    if not images:
        st.warning("No image data available yet. Run apod_scraper.py + database.py to populate the archive.")
        return

    df_images = pd.DataFrame(images)
    category_id_to_name = {c['id']: c['name'] for c in categories}
    df_images['category'] = df_images['category_id'].map(category_id_to_name)

    st.sidebar.title("Filters")
    selected_category = st.sidebar.selectbox("Select Category", options=["All"] + list(category_id_to_name.values()))
    min_year = int(df_images['year'].min())
    max_year = int(df_images['year'].max())
    selected_year = st.sidebar.slider("Select Year", min_value=min_year, max_value=max_year,
                                      value=(min_year, max_year))
    selected_rating = st.sidebar.slider("Select Rating", min_value=0.0, max_value=5.0, value=(0.0, 5.0), step=0.5)

    filtered = df_images.copy()
    if selected_category != "All":
        filtered = filtered[filtered['category'] == selected_category]
    filtered = filtered[(filtered['year'] >= selected_year[0]) & (filtered['year'] <= selected_year[1])]
    filtered = filtered[(filtered['rating'] >= selected_rating[0]) & (filtered['rating'] <= selected_rating[1])]

    if filtered.empty:
        st.warning("No images match the selected filters.")
        return

    # Chart 1: Images by category
    st.subheader("Images by Category")
    by_category = filtered.groupby('category').size().reset_index(name='Count')
    fig_cat = px.bar(by_category, x='category', y='Count', title='Number of Images by Category',
                     labels={"category": "Category", "Count": "Number of Images"}, text='Count')
    fig_cat.update_layout(title_x=0.5)
    st.plotly_chart(fig_cat, use_container_width=True)

    # Chart 2: Images by rating
    st.subheader("Images by Your Rating")
    by_rating = filtered.groupby('rating').size().reset_index(name='Count')
    fig_rating = px.bar(by_rating, x='rating', y='Count', title='Number of Images by Rating',
                        labels={"rating": "Rating", "Count": "Number of Images"}, text='Count')
    fig_rating.update_layout(title_x=0.5)
    st.plotly_chart(fig_rating, use_container_width=True)

    # Gallery: actual images, sorted by rating
    st.subheader("Gallery")
    gallery_sorted = filtered.sort_values('rating', ascending=False)
    cols = st.columns(3)
    for i, (_, row) in enumerate(gallery_sorted.iterrows()):
        with cols[i % 3]:
            st.image(row['image_url'], caption=f"{row['title']} ({row['year']}) — Rating: {row['rating']}",
                     use_container_width=True)
            with st.expander("Details"):
                st.write(f"**Category:** {row['category']}")
                st.write(f"**Topics:** {', '.join(row['topics'])}")
                st.write(row.get('explanation', ''))


# Main app logic
st.sidebar.title("Navigation")
option = st.sidebar.selectbox("Choose a dashboard", ["Categories Dashboard", "Images Dashboard", "Gallery & Visualizations"])

if option == "Gallery & Visualizations":
    visualizations_dashboard()

if api_key_input and validate_api_key(api_key_input):
    if option == "Categories Dashboard":
        categories_dashboard(api_key_input)
    elif option == "Images Dashboard":
        images_dashboard(api_key_input)
elif option in ["Categories Dashboard", "Images Dashboard"]:
    st.error("Invalid API Key or API Key is missing.")
