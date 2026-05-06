"""
fetch_data.py
Run once to pull all data from Open5e API and save to data/ folder.
Usage: python fetch_data.py
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ENDPOINTS = {
    "spells":      "https://api.open5e.com/v1/spells/",
    "spelllist":   "https://api.open5e.com/v1/spelllist/",
    "monsters":    "https://api.open5e.com/v1/monsters/",
    "documents":   "https://api.open5e.com/v1/documents/",
    "backgrounds": "https://api.open5e.com/v1/backgrounds/",
    "planes":      "https://api.open5e.com/v1/planes/",
    "sections":    "https://api.open5e.com/v1/sections/",
    "feats":       "https://api.open5e.com/v1/feats/",
    "conditions":  "https://api.open5e.com/v1/conditions/",
    "races":       "https://api.open5e.com/v1/races/",
    "classes":     "https://api.open5e.com/v1/classes/",
    "magicitems":  "https://api.open5e.com/v1/magicitems/",
    "weapons":     "https://api.open5e.com/v1/weapons/",
    "armor":       "https://api.open5e.com/v1/armor/",
}

# Endpoints that paginate (have next/results structure)
PAGINATED = {
    "spells", "monsters", "backgrounds", "sections",
    "feats", "conditions", "races", "magicitems", "weapons", "armor"
}


def fetch_url(url: str) -> dict:
    """Fetch a URL and return parsed JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": "dnd-chatbot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_pages(url: str, name: str) -> list:
    """Fetch all pages of a paginated endpoint."""
    results = []
    page    = 1
    current = url + "?limit=100"

    while current:
        print(f"  [{name}] page {page} — {current}")
        try:
            data = fetch_url(current)
        except urllib.error.URLError as e:
            print(f"  ERROR fetching {current}: {e}")
            break

        batch = data.get("results", [])
        results.extend(batch)
        current = data.get("next")  # None when last page
        page += 1
        time.sleep(0.3)  # be polite to the API

    return results


def fetch_simple(url: str, name: str) -> list | dict:
    """Fetch a non-paginated endpoint."""
    print(f"  [{name}] {url}")
    try:
        data = fetch_url(url + "?limit=100")
        return data.get("results", data)
    except urllib.error.URLError as e:
        print(f"  ERROR: {e}")
        return []


def save(name: str, data) -> None:
    path = DATA_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    count = len(data) if isinstance(data, list) else "N/A"
    print(f"  ✓ Saved {path.name} ({count} records, {path.stat().st_size // 1024}KB)")


def main():
    print("=" * 55)
    print("  Open5e Data Fetcher")
    print("=" * 55)

    for name, url in ENDPOINTS.items():
        print(f"\n→ Fetching: {name}")

        if name in PAGINATED:
            data = fetch_all_pages(url, name)
        else:
            data = fetch_simple(url, name)

        save(name, data)

    print("\n" + "=" * 55)
    print("  Done! All files saved to backend/data/")
    print("=" * 55)
    print("\nNext steps:")
    print("  1. Delete backend/chroma_db/ to force re-indexing")
    print("  2. Restart: uvicorn main:app --reload --port 8000")


if __name__ == "__main__":
    main()
