"""
dump_raw.py — Dump listing mentah scraper ke tabel raw_scrapes Supabase (Bronze Layer).
Tidak ada filter harga ketat. Semua listing yang punya URL valid masuk.
"""
import hashlib
import json
import urllib.request
from datetime import datetime, timezone

from config import SUPABASE_URL, SUPABASE_SERVICE_KEY


def dump_raw_to_supabase(deals: list):
    """Push daftar deal mentah ke tabel raw_scrapes."""
    if not deals:
        return

    now_ts = datetime.now(timezone.utc).isoformat()
    rows = []

    for d in deals:
        url = d.get("url", "")
        title = d.get("title", "")
        price = d.get("price", 0)
        if not url or not title:
            continue

        source = d.get("source", "")
        if "tokop" in source.lower():
            platform = "Tokopedia"
        elif "fb" in source.lower() or "facebook" in source.lower():
            platform = "Facebook"
        else:
            platform = "Toco"

        rows.append({
            "title": title,
            "price": price,
            "price_raw": d.get("price_raw", ""),
            "description": d.get("description", ""),
            "platform": platform,
            "location": d.get("location", "Indonesia"),
            "url": url,
            "image_url": d.get("image_url", ""),
            "source": source,
            "scraped_at": now_ts,
            "refined": False,
        })

    if not rows:
        return

    api_url = f"{SUPABASE_URL}/rest/v1/raw_scrapes"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates",
    }

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(rows).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            print(f"[+] Raw dump: {len(rows)} listing mentah -> Supabase raw_scrapes (status {resp.status})")
    except Exception as e:
        if hasattr(e, "read"):
            print(f"[-] Raw dump detail: {e.read().decode('utf-8')[:300]}")
        print(f"[-] Gagal dump raw ke Supabase: {e}")
