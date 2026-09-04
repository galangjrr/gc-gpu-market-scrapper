"""
sync_supabase.py — Sinkronisasi deal ke Supabase Cloud (PostgREST upsert).
Semua constants diambil dari config.py.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

from config import (
    SUPABASE_URL, SUPABASE_SERVICE_KEY,
    BANNED_JUNK_BRANDS, BANNED_JUNK_MODELS, BANNED_NON_GPU,
    MIN_PRICE_FLOOR, BRAND_MAP, BRAND_INFERENCE,
    COOLER_TIERS, detect_brand, get_cooler_tier, match_gpu_model,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_gpu_specs(title: str) -> dict:
    """Deteksi brand, fan tier, dan model dari judul listing."""
    brand = detect_brand(title)
    tier_name, _, _ = get_cooler_tier(title)

    # Map tier name ke fan_type display
    tier_display = {
        "S+": "Premium Tier", "S": "Premium Tier",
        "A": "Dual Fan (Standard)", "B": "Entry / Single Fan",
    }
    fan_type = tier_display.get(tier_name, "Dual Fan (Standard)")

    return {"brand": brand, "fan_type": fan_type, "tier": tier_name}


def sync_deals_to_supabase(deals_input: list = None):
    if "YOUR_PROJECT" in SUPABASE_URL:
        print("[-] Supabase URL / Key belum dikonfigurasi. Lewati sync cloud.")
        return

    raw_items = []
    if deals_input:
        for it in deals_input:
            source = it.get("source", "toco")
            if "tokop" in source.lower():
                plat = "Tokopedia"
            elif "fb" in source.lower() or "facebook" in source.lower():
                plat = "Facebook"
            else:
                plat = "Toco"
            raw_items.append((it, plat))
    else:
        files = [os.path.join(BASE_DIR, f) for f in ["tokped_vga_deals.json", "fb_vga_deals.json", "toco_vga_deals.json"]]
        for f_name in files:
            if os.path.exists(f_name):
                try:
                    with open(f_name, "r", encoding="utf-8") as f:
                        plat = "Tokopedia" if "tokped" in f_name else "Facebook" if "fb" in f_name else "Toco"
                        for it in json.load(f):
                            raw_items.append((it, plat))
                except Exception:
                    pass

    now_ts = datetime.now(timezone.utc).isoformat()
    all_deals = []

    import hashlib
    
    for it, platform in raw_items:
        title = it.get("title", "")
        price = it.get("price", 0)

        # Generate deal_hash: gabungan judul + harga (menghalangi spam/reupload dari reseller)
        hash_str = f"{title.lower().strip()}_{price}"
        deal_hash = hashlib.md5(hash_str.encode()).hexdigest()

        # Spesifikasi diekstrak lewat config
        specs = parse_gpu_specs(title)
        
        # Flagging cuan dan status diambil dari deal object yg disuntik hunter.py
        deal_type = it.get("deal_type", "PENDING")
        is_steal_deal = "STEAL_DEAL" in deal_type
        smart_score = it.get("smart_score", 0)

        all_deals.append({
            "title": title,
            "price": price,
            "price_raw": it.get("price_raw", ""),
            "platform": platform,
            "location": it.get("location", "Indonesia"),
            "brand": specs["brand"],
            "fan_type": specs["fan_type"],
            "vram": "-",
            "image_url": it.get("image_url", ""),
            "url": it["url"],
            "is_steal_deal": is_steal_deal,
            "deal_type": deal_type,
            "smart_score": smart_score,
            "deal_hash": deal_hash,
            "created_at": now_ts,
        })

    if not all_deals:
        print("[*] Tidak ada deal untuk disinkronkan.")
        return

    # Kirim ke Supabase REST API (Upsert on deal_hash)
    # Ini menjamin spammer yang upload barang yang sama dengan URL beda tetap di-overwrite!
    api_url = f"{SUPABASE_URL}/rest/v1/vga_deals?on_conflict=deal_hash"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(all_deals).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            if resp.status in [200, 201]:
                print(f"[+] Berhasil sinkronisasi {len(all_deals)} listing ke Supabase Cloud!")
    except Exception as e:
        if hasattr(e, "read"):
            print(f"[-] Supabase 500 Details: {e.read().decode('utf-8')}")
        print(f"[-] Gagal sinkronisasi ke Supabase: {e}")


if __name__ == "__main__":
    sync_deals_to_supabase()
