import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.express as px
from dotenv import load_dotenv
import os

load_dotenv()
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000/api')
try:
    from api_key import API_KEY as LOCAL_API_KEY
except ImportError:
    LOCAL_API_KEY = ""

AUTH_API_KEY = os.getenv('API_KEY') or LOCAL_API_KEY

# Set page config
st.set_page_config(page_title="APOD Personal Gallery", layout="wide")


def api_headers():
    if AUTH_API_KEY:
        return {"api-key": AUTH_API_KEY}
    return None


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
    st.title("📊 Gallery & Visualizations")
    st.markdown("*Browse and explore your archived images*")
    st.divider()

    try:
        images = get_images()
        categories = get_categories()
    except Exception as e:
        st.error(f"Could not connect to API: {e}")
        st.info("Make sure FastAPI is running: `uvicorn main:app --reload`")
        return

    if not images:
        st.warning("No image data available yet.")
        with st.expander("📖 How to populate the archive:"):
            st.markdown("""
            1. **Setup environment**: `cp .env.example .env` and edit with your NASA_API_KEY
            2. **Initialize database**: `python -c "from database import create_database; create_database()"`
            3. **Fetch APOD data**: `python -c "from apod_scraper import scrape_apod_range; from datetime import date, timedelta; scrape_apod_range(date.today() - timedelta(days=14), date.today())"`
            4. **Start API**: In a terminal run `uvicorn main:app --reload`
            5. **Refresh this page**
            """)
        return

    df_images = pd.DataFrame(images)
    category_id_to_name = {c['id']: c['name'] for c in categories}
    df_images['category'] = df_images['category_id'].map(category_id_to_name)

    st.sidebar.title("🔍 Filters")
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


# ---------- Favorites Gallery Dashboard ----------
def favorites_gallery():
    """Display personal favorites with ratings and timeline."""
    st.title("⭐ Personal Favorites Gallery")
    st.markdown("*Your curated collection of astronomy's greatest moments*")
    st.divider()

    try:
        images = get_images()
        categories = get_categories()
    except Exception as e:
        st.error(f"Could not connect to API: {e}")
        st.info("Make sure FastAPI is running: `uvicorn main:app --reload`")
        return

    if not images:
        st.info("No images in your gallery yet. Use the 'Manage Images' section to add some!")
        return

    df_images = pd.DataFrame(images)
    category_id_to_name = {c['id']: c['name'] for c in categories}
    df_images['category'] = df_images['category_id'].map(category_id_to_name)

    # Sidebar filters
    st.sidebar.title("🔍 Filter & Sort")
    
    # Filter by rating (favorites first)
    min_rating = st.sidebar.slider("Minimum Rating", 0.0, 5.0, 0.0, step=0.5)
    
    # Filter by category
    categories_list = sorted(set(df_images['category']))
    selected_categories = st.sidebar.multiselect("Categories", categories_list, default=categories_list)
    
    # Filter by year
    min_year = int(df_images['year'].min())
    max_year = int(df_images['year'].max())
    selected_year_range = st.sidebar.slider("Year Range", min_year, max_year, (min_year, max_year))
    
    # Sort options
    sort_by = st.sidebar.selectbox("Sort By", ["Rating (High to Low)", "Rating (Low to High)", "Date (Newest)", "Date (Oldest)"])

    # Apply filters
    filtered = df_images.copy()
    filtered = filtered[filtered['rating'] >= min_rating]
    filtered = filtered[filtered['category'].isin(selected_categories)]
    filtered = filtered[(filtered['year'] >= selected_year_range[0]) & (filtered['year'] <= selected_year_range[1])]

    # Apply sorting
    if sort_by == "Rating (High to Low)":
        filtered = filtered.sort_values('rating', ascending=False)
    elif sort_by == "Rating (Low to High)":
        filtered = filtered.sort_values('rating', ascending=True)
    elif sort_by == "Date (Newest)":
        filtered = filtered.sort_values('capture_date', ascending=False)
    else:  # Date (Oldest)
        filtered = filtered.sort_values('capture_date', ascending=True)

    if filtered.empty:
        st.warning("No images match your filters.")
        return

    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total in Collection", len(filtered))
    with col2:
        avg_rating = filtered['rating'].mean()
        st.metric("Average Rating", f"{avg_rating:.1f}/5.0")
    with col3:
        favorites = len(filtered[filtered['rating'] >= 4.0])
        st.metric("Top Favorites (4+)", favorites)
    with col4:
        year_range_str = f"{filtered['year'].min()}-{filtered['year'].max()}"
        st.metric("Span", year_range_str)

    st.divider()

    # Gallery display with 3-column layout
    st.markdown("### ✨ Gallery")
    cols = st.columns(3)
    for i, (_, row) in enumerate(filtered.iterrows()):
        col = cols[i % 3]
        with col:
            # Image card with visual feedback for rating
            rating_stars = "⭐" * int(row['rating']) + "☆" * (5 - int(row['rating']))
            
            st.image(row['image_url'], use_container_width=True)
            st.markdown(f"**{row['title']}**")
            st.caption(f"{row['capture_date']} • {row['year']} • {row['category']}")
            
            with st.expander(f"View Details {rating_stars}"):
                st.write(f"**Rating:** {row['rating']}/5.0")
                st.write(f"**Category:** {row['category']}")
                if row['topics']:
                    st.write(f"**Topics:** {', '.join(row['topics'])}")
                st.write(f"**Explanation:**")
                st.write(row.get('explanation', 'No explanation available.'))
                
                if AUTH_API_KEY:
                    col_edit, col_del = st.columns(2)
                    with col_edit:
                        if st.button("✏️ Edit", key=f"edit_{row['id']}"):
                            st.session_state.edit_image_id = row['id']
                    with col_del:
                        if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                            delete_image(AUTH_API_KEY, row['id'])
                            st.rerun()


# ---------- Archive & Statistics Dashboard ----------
def archive_dashboard():
    """Browse archive with rich statistics and filtering."""
    st.title("📚 Archive & Statistics")
    st.markdown("*Explore your astronomy collection over time*")
    st.divider()

    try:
        images = get_images()
        categories = get_categories()
    except Exception as e:
        st.error(f"Could not connect to API: {e}")
        return

    if not images:
        st.info("Your archive is empty. Add images to get started!")
        return

    df_images = pd.DataFrame(images)
    category_id_to_name = {c['id']: c['name'] for c in categories}
    df_images['category'] = df_images['category_id'].map(category_id_to_name)

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Statistics", "🗂️ By Category", "📅 Timeline"])

    with tab1:
        st.subheader("Collection Overview")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Images", len(df_images))
        with col2:
            st.metric("Years Covered", f"{df_images['year'].min()}-{df_images['year'].max()}")
        with col3:
            st.metric("Unique Categories", df_images['category'].nunique())

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Rating Distribution")
            fig_rating = px.histogram(df_images, x='rating', nbins=10, 
                                     title="Images by Your Rating",
                                     labels={"rating": "Rating", "count": "Count"})
            st.plotly_chart(fig_rating, use_container_width=True)
        
        with col2:
            st.markdown("#### Top Categories")
            top_cats = df_images['category'].value_counts().head(10)
            fig_cat = px.bar(x=top_cats.values, y=top_cats.index, orientation='h',
                            title="Top 10 Categories",
                            labels={"x": "Count", "y": "Category"})
            st.plotly_chart(fig_cat, use_container_width=True)

        # Images by year
        st.markdown("#### Images by Year")
        images_by_year = df_images.groupby('year').size().reset_index(name='Count')
        fig_year = px.line(images_by_year, x='year', y='Count',
                          title="Archive Growth Over Time", markers=True)
        st.plotly_chart(fig_year, use_container_width=True)

    with tab2:
        st.subheader("Browse by Category")
        categories_list = sorted(df_images['category'].unique())
        
        for category in categories_list:
            cat_images = df_images[df_images['category'] == category]
            avg_rating = cat_images['rating'].mean()
            
            with st.expander(f"📌 {category} ({len(cat_images)} images, avg rating: {avg_rating:.1f})"):
                # Show images in this category
                cols = st.columns(3)
                for i, (_, row) in enumerate(cat_images.iterrows()):
                    with cols[i % 3]:
                        st.image(row['image_url'], use_container_width=True)
                        st.caption(f"{row['title']} ({row['year']}) - {row['rating']}/5.0")

    with tab3:
        st.subheader("Timeline View")
        # Sort by date
        df_timeline = df_images.sort_values('capture_date', ascending=False)
        
        for _, row in df_timeline.iterrows():
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(row['image_url'], width=100)
            with col2:
                rating_stars = "⭐" * int(row['rating'])
                st.markdown(f"**{row['title']}** {rating_stars}")
                st.caption(f"{row['capture_date']} • {row['category']}")
                st.write(row.get('explanation', '')[:200] + "...")
                if st.button("View Full", key=f"timeline_{row['id']}"):
                    st.session_state.selected_image_id = row['id']


# Main app logic
st.title("🌌 APOD Personal Gallery")
st.markdown("*Daily images from NASA's Astronomy Picture of the Day — rate, categorize, and build your personal favorites collection*")
st.divider()

if not AUTH_API_KEY:
    st.warning("⚠️ No API key found. Add your key to `.env` or `astronomy/api_key.py` to enable image management.")

# Sidebar navigation
with st.sidebar:
    st.divider()
    st.title("📍 Navigation")
    page = st.radio(
        "Choose a view",
        ["⭐ Favorites", "📚 Archive", "🛠️ Manage", "📚 Categories"],
        help="Explore your personal astronomy collection"
    )

# Render selected page
if page == "⭐ Favorites":
    favorites_gallery()

elif page == "📚 Archive":
    archive_dashboard()

elif page == "🛠️ Manage":
    if AUTH_API_KEY:
        st.title("🛠️ Manage Your Collection")
        st.markdown("*Add, edit, or delete images from your archive*")
        st.divider()
        
        sub_page = st.radio("Choose action", ["Add Image", "Edit Image", "View All"])
        
        if sub_page == "Add Image":
            images_dashboard(AUTH_API_KEY)
        elif sub_page == "Edit Image":
            try:
                images = get_images()
                categories = get_categories()
                if images:
                    st.markdown("### Edit Existing Image")
                    selected_title = st.selectbox("Select Image", options=[img['title'] for img in images])
                    img = next((i for i in images if i['title'] == selected_title), None)
                    if img:
                        category_id_to_name = {c['id']: c['name'] for c in categories}
                        cat_name = category_id_to_name.get(img['category_id'], categories[0]['name'] if categories else "")
                        cat_names = [c['name'] for c in categories]
                        
                        new_rating = st.slider("Update Rating", 0.0, 5.0, float(img['rating']), 0.5)
                        update_button = st.button("Update Rating")
                        
                        if update_button:
                            selected_category_id = next((c['id'] for c in categories if c['name'] == cat_name), None)
                            image_data = {
                                "title": img['title'],
                                "category_id": selected_category_id,
                                "image_url": img['image_url'],
                                "explanation": img.get('explanation', ''),
                                "topics": img.get('topics', []),
                                "capture_date": img.get('capture_date', ''),
                                "year": img['year'],
                                "rating": new_rating
                            }
                            update_image(AUTH_API_KEY, img['id'], image_data)
                            st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        else:  # View All
            try:
                images = get_images()
                categories = get_categories()
                if images:
                    category_map = {c['id']: c['name'] for c in categories}
                    table_rows = []
                    for img in images:
                        row = dict(img)
                        row['category'] = category_map.get(row['category_id'], 'Unknown')
                        row['topics'] = ', '.join(row['topics']) if row['topics'] else ''
                        table_rows.append(row)
                    df = pd.DataFrame(table_rows)
                    display_cols = [c for c in ['id', 'title', 'category', 'rating', 'year', 'capture_date'] if c in df.columns]
                    st.dataframe(df[display_cols], use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Image management is disabled. Configure an API key first.")

elif page == "📚 Categories":
    if AUTH_API_KEY:
        categories_dashboard(AUTH_API_KEY)
    else:
        st.warning("Category management is disabled. Configure an API key first.")
        st.divider()
        st.subheader("📚 Available Categories")
        try:
            categories = get_categories()
            if categories:
                cols = st.columns(3)
                for i, cat in enumerate(categories):
                    with cols[i % 3]:
                        st.info(f"📌 {cat['name']}")
            else:
                st.info("No categories configured yet.")
        except Exception as e:
            st.error(f"Could not fetch categories: {e}")
