import os
import random
from datetime import date, timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000/api").rstrip("/")
EARLIEST_APOD_DATE = date(2000, 1, 1)
GALLERY_PAGE_SIZE = 12
MONTHS = [
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
]

CUSTOM_CSS = """
<style>
.stApp {
    background:
        radial-gradient(ellipse at top, rgba(76, 58, 140, 0.35), transparent 60%),
        radial-gradient(ellipse at bottom right, rgba(20, 90, 140, 0.25), transparent 55%),
        #0b0d1a;
}
.stApp .hero-title {
    font-size: 2.6rem !important;
    line-height: 1.15;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #f5d98b, #e58fdb 50%, #8fb8ff);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    margin-bottom: 0;
}
.stApp .hero-subtitle { color: #a9b0cf; margin-top: 0.2rem; font-size: 1.05rem; }
.apod-title { font-size: 1.9rem; font-weight: 700; margin: 0.4rem 0 0.2rem; }
.chip {
    display: inline-block;
    padding: 0.15rem 0.7rem;
    margin: 0 0.4rem 0.4rem 0;
    border-radius: 999px;
    background: rgba(143, 184, 255, 0.12);
    border: 1px solid rgba(143, 184, 255, 0.35);
    color: #cfdcff;
    font-size: 0.82rem;
}
.explanation { font-size: 1.05rem; line-height: 1.7; color: #dde2f5; }
.card-title { font-weight: 600; margin: 0.3rem 0 0; line-height: 1.3; }
.card-date { color: #a9b0cf; font-size: 0.85rem; }
</style>
"""


class _ExplanationParser(HTMLParser):
    """Convert APOD explanation markup into readable Streamlit markdown."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._link_href = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            self._link_href = href
            self.parts.append("[")
        elif tag in {"br", "p", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "a":
            if self._link_href:
                self.parts.append(f"]({self._link_href})")
            else:
                self.parts.append("]")
            self._link_href = None
        elif tag in {"p", "div"}:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def clean_explanation(explanation):
    """Remove HTML tags while preserving readable text and simple links."""
    parser = _ExplanationParser()
    parser.feed(explanation or "")
    parser.close()
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    return "\n\n".join(line for line in lines if line)


def playable_video_url(url):
    """Turn YouTube embed links (which NASA uses) into links st.video can play."""
    parsed = urlparse(url or "")
    if "youtube" in parsed.netloc and parsed.path.startswith("/embed/"):
        video_id = parsed.path.split("/")[2]
        start = parse_qs(parsed.query).get("start")
        suffix = f"&t={start[0]}" if start else ""
        return f"https://www.youtube.com/watch?v={video_id}{suffix}"
    return url


def error_detail(response):
    """Return the API's error message, falling back to the status code."""
    try:
        body = response.json()
    except ValueError:
        body = None
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, list):
        detail = "; ".join(item.get("msg", "") for item in detail)
    return detail or f"status {response.status_code}"


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------


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


@st.cache_data(ttl=600, show_spinner=False)
def get_apod_entry(date_text):
    """Load an APOD entry; the API fetches it from NASA when it is not saved yet.

    Returns ``(entry, error_message)``.
    """
    response = requests.get(f"{BASE_URL}/apod/{date_text}", timeout=60)
    if response.ok:
        return response.json(), None
    return None, error_detail(response)


@st.cache_data(ttl=120, show_spinner=False)
def get_gallery_page(year, month, search, page, sort="desc", page_size=GALLERY_PAGE_SIZE):
    params = {"page": page, "page_size": page_size, "sort": sort}
    if year:
        params["year"] = year
    if month:
        params["month"] = month
    if search:
        params["search"] = search
    response = requests.get(f"{BASE_URL}/apod/entries", params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def refresh_cached_data():
    get_apod_entry.clear()
    get_gallery_page.clear()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def display_media(apod, in_card=False):
    url = apod.get("url")
    if not url:
        st.warning("No media URL is available for this APOD.")
    elif apod.get("media_type") == "video":
        if in_card:
            st.link_button("▶ Watch video", url, width="stretch")
        else:
            st.video(playable_video_url(url))
    elif apod.get("media_type") == "image":
        st.image(url, width="stretch")
    else:
        st.link_button("Open media", url, width="stretch")


def display_apod(apod):
    """Display one APOD in the same order as the NASA APOD page."""
    display_media(apod)

    st.markdown(f'<div class="apod-title">{_escape(apod["title"])}</div>', unsafe_allow_html=True)
    chips = [date.fromisoformat(apod["date"]).strftime("%A, %d %B %Y")]
    chips.append("🎬 Video" if apod.get("media_type") == "video" else "🖼️ Image")
    if apod.get("copyright"):
        chips.append(f"© {apod['copyright'].strip()}")
    st.markdown(
        "".join(f'<span class="chip">{_escape(chip)}</span>' for chip in chips),
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(clean_explanation(apod.get("explanation", "")))

    if apod.get("hdurl"):
        st.link_button("🔭 View full-resolution image", apod["hdurl"])


def _escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


def _shift_selected_date(days):
    new_date = st.session_state.selected_date + timedelta(days=days)
    st.session_state.selected_date = min(max(new_date, EARLIEST_APOD_DATE), date.today())


def _random_selected_date():
    span = (date.today() - EARLIEST_APOD_DATE).days
    st.session_state.selected_date = EARLIEST_APOD_DATE + timedelta(days=random.randint(0, span))


def show_public_view():
    """Show the public daily-picture view."""
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = date.today()

    picker, previous_day, next_day, surprise = st.columns(
        [3, 1, 1, 1], vertical_alignment="bottom"
    )
    picker.date_input(
        "Choose a date",
        min_value=EARLIEST_APOD_DATE,
        max_value=date.today(),
        key="selected_date",
    )
    previous_day.button(
        "◀ Previous",
        on_click=_shift_selected_date,
        args=(-1,),
        width="stretch",
        disabled=st.session_state.selected_date <= EARLIEST_APOD_DATE,
    )
    next_day.button(
        "Next ▶",
        on_click=_shift_selected_date,
        args=(1,),
        width="stretch",
        disabled=st.session_state.selected_date >= date.today(),
    )
    surprise.button("🎲 Surprise me", on_click=_random_selected_date, width="stretch")

    try:
        with st.spinner("Looking up that day's picture..."):
            apod, error = get_apod_entry(st.session_state.selected_date.isoformat())
    except requests.RequestException:
        st.error("The backend is not available. Start the FastAPI server first.")
        return

    if error:
        st.warning(f"No picture for this day: {error}")
    elif apod:
        display_apod(apod)


def _open_in_daily_view(date_text):
    st.session_state.selected_date = date.fromisoformat(date_text)
    st.session_state.view = "🌌 Picture of the day"


def show_gallery_view():
    """Show a filterable grid of the pictures saved in the database."""
    year_col, month_col, search_col, sort_col = st.columns([1, 1, 2, 1])
    years = ["All"] + list(range(date.today().year, EARLIEST_APOD_DATE.year - 1, -1))
    year = year_col.selectbox("Year", years)
    month_name = month_col.selectbox("Month", ["All"] + MONTHS)
    search = search_col.text_input("Search titles and explanations", placeholder="e.g. nebula")
    sort = sort_col.selectbox("Order", ["Newest first", "Oldest first"])

    filters = (year, month_name, search, sort)
    if st.session_state.get("gallery_filters") != filters:
        st.session_state.gallery_filters = filters
        st.session_state.gallery_page = 1
    page = st.session_state.get("gallery_page", 1)

    try:
        entries = get_gallery_page(
            None if year == "All" else year,
            None if month_name == "All" else MONTHS.index(month_name) + 1,
            search.strip() or None,
            page,
            "desc" if sort == "Newest first" else "asc",
        )
    except requests.RequestException:
        st.error("The backend is not available. Start the FastAPI server first.")
        return

    if not entries:
        st.info(
            "No saved pictures match these filters. Pictures are saved as you "
            "browse, or an admin can sync them from NASA."
        )
        return

    for row_start in range(0, len(entries), 3):
        columns = st.columns(3)
        for column, apod in zip(columns, entries[row_start:row_start + 3]):
            with column.container(border=True):
                display_media(apod, in_card=True)
                st.markdown(
                    f'<div class="card-title">{_escape(apod["title"])}</div>'
                    f'<div class="card-date">{apod["date"]}</div>',
                    unsafe_allow_html=True,
                )
                st.button(
                    "Open",
                    key=f"open_{apod['id']}",
                    on_click=_open_in_daily_view,
                    args=(apod["date"],),
                    width="stretch",
                )

    previous_page, page_label, next_page = st.columns([1, 2, 1], vertical_alignment="center")
    if previous_page.button("◀ Newer" if sort == "Newest first" else "◀ Older",
                            disabled=page == 1, width="stretch"):
        st.session_state.gallery_page = page - 1
        st.rerun()
    page_label.markdown(f"<div style='text-align:center'>Page {page}</div>", unsafe_allow_html=True)
    if next_page.button("Older ▶" if sort == "Newest first" else "Newer ▶",
                        disabled=len(entries) < GALLERY_PAGE_SIZE, width="stretch"):
        st.session_state.gallery_page = page + 1
        st.rerun()


def _entry_form(form_key, entry=None, submit_label="Save"):
    """Render the add/edit form and return the submitted entry, or None."""
    entry = entry or {}
    # Keys include the entry id so switching entries shows that entry's values.
    suffix = f"{form_key}_{entry.get('id', 'new')}"
    media_types = ["image", "video", "other"]
    with st.form(f"form_{suffix}"):
        left, right = st.columns(2)
        entry_date = left.date_input(
            "Date",
            value=date.fromisoformat(entry["date"]) if entry.get("date") else date.today(),
            min_value=EARLIEST_APOD_DATE,
            max_value=date.today(),
            key=f"date_{suffix}",
        )
        media_type = right.selectbox(
            "Media type",
            media_types,
            index=media_types.index(entry.get("media_type", "image"))
            if entry.get("media_type") in media_types
            else 0,
            key=f"media_{suffix}",
        )
        title = st.text_input("Title", value=entry.get("title", ""), key=f"title_{suffix}")
        explanation = st.text_area(
            "Explanation",
            value=entry.get("explanation") or "",
            height=160,
            key=f"explanation_{suffix}",
        )
        url = st.text_input(
            "Image or video URL", value=entry.get("url") or "", key=f"url_{suffix}"
        )
        hdurl = st.text_input(
            "HD image URL (optional)", value=entry.get("hdurl") or "", key=f"hdurl_{suffix}"
        )
        copyright_text = st.text_input(
            "Copyright (optional)",
            value=entry.get("copyright") or "",
            key=f"copyright_{suffix}",
        )
        submitted = st.form_submit_button(submit_label, type="primary")

    if not submitted:
        return None
    if not title.strip() or not url.strip():
        st.error("Title and URL are required.")
        return None
    return {
        "date": entry_date.isoformat(),
        "title": title.strip(),
        "explanation": explanation,
        "url": url.strip(),
        "hdurl": hdurl.strip() or None,
        "media_type": media_type,
        "copyright": copyright_text.strip() or None,
    }


def _send(method, path, headers, success_message, **kwargs):
    """Call the API, show the outcome and refresh the page on success."""
    try:
        response = requests.request(
            method, f"{BASE_URL}{path}", headers=headers, timeout=kwargs.pop("timeout", 15), **kwargs
        )
    except requests.RequestException:
        st.error("Could not connect to the backend.")
        return None
    if response.ok:
        refresh_cached_data()
        st.toast(success_message, icon="✅")
        return response.json()
    st.error(f"Request failed: {error_detail(response)}")
    return None


def show_admin_view(api_key):
    """Show APOD management tools for a valid API key."""
    headers = {"api-key": api_key}

    search = st.text_input("Find saved entries", placeholder="Search by title or text")
    try:
        entries = get_gallery_page(None, None, search.strip() or None, 1, "desc", 100)
    except requests.RequestException:
        st.error("The backend is not available.")
        return

    saved_tab, add_tab, edit_tab, nasa_tab = st.tabs(
        ["📋 Saved entries", "➕ Add", "✏️ Edit or delete", "🛰️ NASA"]
    )

    with saved_tab:
        if entries:
            st.caption(f"Showing the {len(entries)} most recent matching entries.")
            st.dataframe(
                entries,
                width="stretch",
                hide_index=True,
                column_order=["date", "title", "media_type", "copyright", "url"],
                column_config={
                    "date": "Date",
                    "title": "Title",
                    "media_type": "Type",
                    "copyright": "Copyright",
                    "url": st.column_config.LinkColumn("Media"),
                },
            )
        else:
            st.info("No saved entries yet.")

    with add_tab:
        new_entry = _entry_form("add", submit_label="Add entry")
        if new_entry and _send("POST", "/apod/", headers, "Entry added.", json=new_entry):
            st.rerun()

    with edit_tab:
        if not entries:
            st.info("No saved entries to edit.")
        else:
            entry_options = {f"{entry['date']} · {entry['title']}": entry for entry in entries}
            selected_label = st.selectbox("Entry", list(entry_options))
            selected_entry = entry_options[selected_label]

            updated_entry = _entry_form("edit", selected_entry, "Save changes")
            if updated_entry and _send(
                "PUT", f"/apod/{selected_entry['id']}", headers, "Entry updated.",
                json=updated_entry,
            ):
                st.rerun()

            with st.expander("Delete this entry"):
                confirm = st.checkbox(
                    f"Yes, delete “{selected_entry['title']}”",
                    key=f"confirm_delete_{selected_entry['id']}",
                )
                if st.button("Delete entry", type="primary", disabled=not confirm) and _send(
                    "DELETE", f"/apod/{selected_entry['id']}", headers, "Entry deleted."
                ):
                    st.rerun()

    with nasa_tab:
        st.markdown("##### Fetch one day")
        fetch_col, button_col = st.columns([3, 1], vertical_alignment="bottom")
        fetch_date = fetch_col.date_input(
            "Date to fetch",
            value=date.today(),
            min_value=EARLIEST_APOD_DATE,
            max_value=date.today(),
            key="fetch_date",
        )
        if button_col.button("Fetch from NASA", width="stretch"):
            with st.spinner("Fetching from NASA..."):
                apod = _send(
                    "POST", "/apod/fetch", headers, "APOD fetched from NASA.",
                    params={"date": fetch_date.isoformat()}, timeout=120,
                )
            if apod:
                st.success(f"Saved “{apod['title']}”.")

        st.divider()
        st.markdown("##### Sync history")
        st.caption(
            "Saves every missing picture from today back to the chosen date. "
            "Going far back takes many requests to NASA."
        )
        sync_col, sync_button_col = st.columns([3, 1], vertical_alignment="bottom")
        sync_start = sync_col.date_input(
            "Sync back to",
            value=date.today() - timedelta(days=30),
            min_value=EARLIEST_APOD_DATE,
            max_value=date.today(),
            key="sync_start",
        )
        if sync_button_col.button("Start sync", width="stretch"):
            with st.spinner("Syncing with NASA. This can take a while..."):
                summary = _send(
                    "POST", "/apod/sync", headers, "Sync finished.",
                    params={"start_date": sync_start.isoformat()}, timeout=1800,
                )
            if summary:
                inserted, duplicates, failed = st.columns(3)
                inserted.metric("New pictures", summary["inserted"])
                duplicates.metric("Already saved", summary["duplicates"])
                failed.metric("Failed pages", summary["failed"])


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


st.set_page_config(
    page_title="Astronomy Picture of the Day",
    page_icon="🔭",
    layout="wide",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown('<div class="hero-title">Astronomy Picture of the Day</div>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-subtitle">A new view of the universe every day, from NASA\'s APOD archive.</p>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 🔭 APOD Explorer")
    view = st.radio(
        "View",
        ["🌌 Picture of the day", "🖼️ Gallery", "🛠️ Admin"],
        key="view",
        label_visibility="collapsed",
    )

if view == "🌌 Picture of the day":
    show_public_view()
elif view == "🖼️ Gallery":
    show_gallery_view()
else:
    with st.sidebar:
        st.divider()
        api_key = st.text_input("API key", type="password")
    if not api_key:
        st.info("Enter your API key in the sidebar to open the admin tools.")
    elif not validate_api_key(api_key):
        st.sidebar.error("Invalid API key.")
    else:
        st.sidebar.success("Signed in.")
        show_admin_view(api_key)
