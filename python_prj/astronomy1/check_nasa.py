"""Check how quickly this computer can reach NASA's APOD service.

Run it from this folder with:  python check_nasa.py
"""
import time
from datetime import date, timedelta

import nasa_fetcher


def timed(label, call):
    started = time.perf_counter()
    try:
        result = call()
        outcome = f"OK: {result['date']} {result['title']}"
    except Exception as exc:  # report every failure, this is a diagnostic
        outcome = f"FAILED: {exc}"
    print(f"{label:<28} {time.perf_counter() - started:5.1f}s  {outcome}")


if __name__ == "__main__":
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last_year = (date.today() - timedelta(days=365)).isoformat()
    timed("Latest picture", nasa_fetcher.fetch_apod)
    timed(f"Yesterday ({yesterday})", lambda: nasa_fetcher.fetch_apod(yesterday))
    timed(f"A year ago ({last_year})", lambda: nasa_fetcher.fetch_apod(last_year))
