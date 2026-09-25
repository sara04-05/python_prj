import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000/api").rstrip("/")


def validate_api_key(api_key):
    """Return True when the API accepts the supplied key."""
    try:
        response = requests.get(
            f"{BASE_URL}/validate_key/",
            headers={"api-key": api_key},
            timeout=10,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_apod_entry(selected_date):
    """Load an APOD entry, fetching it from NASA when it is not saved yet."""
    date_text = selected_date.isoformat()
    response = requests.get(f"{BASE_URL}/apod/{date_text}", timeout=10)

    if response.status_code == 404:
        api_key = os.getenv("API_KEYS")
        fetch_response = requests.post(
            f"{BASE_URL}/apod/fetch",
            params={"date": date_text},
            headers={"api-key": api_key} if api_key else {},
            timeout=30,
        )
        if fetch_response.ok:
            return fetch_response.json()
        st.error(
            f"Could not fetch this picture from NASA "
            f"(status {fetch_response.status_code})."
        )
        return None

    if response.ok:
        return response.json()

    st.error(f"Could not load the picture (status {response.status_code}).")
    return None


def display_apod(apod):
    """Display one APOD in the same order as the NASA APOD page."""
    st.header(apod["title"])
    st.write(f"Date: {apod['date']}")

    media_url = apod.get("url")
    if not media_url:
        st.warning("This APOD does not have a media URL.")
    elif apod.get("media_type") == "video":
        st.video(media_url)
    else:
        st.image(media_url, use_container_width=True)

    st.subheader("Explanation")
    st.write(apod.get("explanation", ""))
    if apod.get("copyright"):
        st.caption(f"Copyright: {apod['copyright']}")


def show_public_view():
    """Show the public daily-picture view."""
    selected_date = st.date_input("Choose a date", value=date.today())

    try:
        apod = get_apod_entry(selected_date)
    except requests.RequestException:
        st.error("The backend is not available. Start the FastAPI server first.")
        return

    if apod:
        display_apod(apod)


def show_admin_view(api_key):
    """Show APOD management tools for a valid API key."""
    headers = {"api-key": api_key}

    try:
        response = requests.get(f"{BASE_URL}/apod/", headers=headers, timeout=10)
    except requests.RequestException:
        st.error("The backend is not available.")
        return

    if not response.ok:
        st.error(f"Could not load saved entries (status {response.status_code}).")
        return

    entries = response.json()
    st.dataframe(entries, use_container_width=True)

    st.subheader("Add an entry")
    with st.form("add_apod_form"):
        add_date = st.date_input("Date", value=date.today(), key="add_date")
        add_title = st.text_input("Title")
        add_explanation = st.text_area("Explanation")
        add_url = st.text_input("Image or video URL")
        add_hdurl = st.text_input("HD image URL")
        add_media_type = st.selectbox("Media type", ["image", "video"])
        add_copyright = st.text_input("Copyright")
        add_submitted = st.form_submit_button("Add entry")

    if add_submitted:
        new_entry = {
            "date": add_date.isoformat(),
            "title": add_title,
            "explanation": add_explanation,
            "url": add_url,
            "hdurl": add_hdurl or None,
            "media_type": add_media_type,
            "copyright": add_copyright or None,
        }
        try:
            add_response = requests.post(
                f"{BASE_URL}/apod/", json=new_entry, headers=headers, timeout=10
            )
            if add_response.ok:
                st.success("Entry added.")
                st.rerun()
            else:
                st.error(
                    f"Could not add the entry (status {add_response.status_code})."
                )
        except requests.RequestException:
            st.error("Could not connect to the backend.")

    if entries:
        entry_options = {f"{entry['date']} - {entry['title']}": entry for entry in entries}
        selected_label = st.selectbox("Select an entry to edit", list(entry_options))
        selected_entry = entry_options[selected_label]

        st.subheader("Edit entry")
        with st.form("edit_apod_form"):
            edit_date = st.date_input(
                "Date", value=date.fromisoformat(selected_entry["date"]), key="edit_date"
            )
            edit_title = st.text_input("Title", value=selected_entry["title"], key="edit_title")
            edit_explanation = st.text_area(
                "Explanation",
                value=selected_entry.get("explanation") or "",
                key="edit_explanation",
            )
            edit_url = st.text_input(
                "Image or video URL", value=selected_entry.get("url") or "", key="edit_url"
            )
            edit_hdurl = st.text_input(
                "HD image URL", value=selected_entry.get("hdurl") or "", key="edit_hdurl"
            )
            edit_media_type = st.selectbox(
                "Media type",
                ["image", "video"],
                index=0 if selected_entry.get("media_type") == "image" else 1,
                key="edit_media_type",
            )
            edit_copyright = st.text_input(
                "Copyright",
                value=selected_entry.get("copyright") or "",
                key="edit_copyright",
            )
            edit_submitted = st.form_submit_button("Update entry")

        if edit_submitted:
            updated_entry = {
                "date": edit_date.isoformat(),
                "title": edit_title,
                "explanation": edit_explanation,
                "url": edit_url,
                "hdurl": edit_hdurl or None,
                "media_type": edit_media_type,
                "copyright": edit_copyright or None,
            }
            try:
                edit_response = requests.put(
                    f"{BASE_URL}/apod/{selected_entry['id']}",
                    json=updated_entry,
                    headers=headers,
                    timeout=10,
                )
                if edit_response.ok:
                    st.success("Entry updated.")
                    st.rerun()
                else:
                    st.error(
                        f"Could not update the entry "
                        f"(status {edit_response.status_code})."
                    )
            except requests.RequestException:
                st.error("Could not connect to the backend.")

        st.subheader("Delete entry")
        if st.button("Delete selected entry"):
            try:
                delete_response = requests.delete(
                    f"{BASE_URL}/apod/{selected_entry['id']}",
                    headers=headers,
                    timeout=10,
                )
                if delete_response.ok:
                    st.success("Entry deleted.")
                    st.rerun()
                else:
                    st.error(
                        f"Could not delete the entry "
                        f"(status {delete_response.status_code})."
                    )
            except requests.RequestException:
                st.error("Could not connect to the backend.")

    fetch_date = st.date_input("Date to fetch", value=date.today(), key="fetch_date")
    if st.button("Fetch from NASA"):
        try:
            fetch_response = requests.post(
                f"{BASE_URL}/apod/fetch",
                params={"date": fetch_date.isoformat()},
                headers=headers,
                timeout=30,
            )
            if fetch_response.ok:
                st.success("APOD fetched from NASA.")
                st.rerun()
            else:
                st.error(
                    f"Could not fetch the APOD "
                    f"(status {fetch_response.status_code})."
                )
        except requests.RequestException:
            st.error("Could not connect to the backend.")


st.set_page_config(page_title="Astronomy Picture of the Day")
st.title("Astronomy Picture of the Day")

view = st.sidebar.selectbox("View", ["APOD", "Admin"])

if view == "APOD":
    show_public_view()
else:
    api_key = st.sidebar.text_input("API key", type="password")
    if api_key:
        if validate_api_key(api_key):
            show_admin_view(api_key)
        else:
            st.sidebar.error("Invalid API key.")
    else:
        st.info("Enter an API key in the sidebar to open the admin view.")
