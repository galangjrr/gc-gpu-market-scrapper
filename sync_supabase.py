import json
import os
import urllib.request
import urllib.parse
from generate_dashboard import parse_gpu_specs

# KONFIGURASI SUPABASE (Isi dari Dashboard Supabase Anda)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://YOUR_PROJECT_ID.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "YOUR_SUPABASE_SERVICE_ROLE_KEY")

def sync_deals_to_supabase():
    if "YOUR_PROJECT" in SUPABASE_URL:
        print("[-] Supabase URL / Key belum dikonfigurasi. Lewati sync cloud.")
        return

    files = ["tokped_vga_deals.json", "fb_vga_deals.json", "toco_vga_deals.json"]
    all_deals = []
    
    for f_name in files:
        if os.path.exists(f_name):
            try:
                with open(f_name, "r", encoding="utf-8") as f:
                    platform = "Tokopedia" if "tokped" in f_name else "Facebook" if "fb" in f_name else "Toco"
                    items = json.load(f)
                    for it in items:
                        specs = parse_gpu_specs(it.get("title", ""))
                        all_deals.append({
                            "title": it.get("title", ""),
                            "price": it.get("price", 0),
                            "price_raw": it.get("price_raw", ""),
                            "platform": platform,
                            "location": it.get("location", "Indonesia"),
                            "brand": specs.get("brand", "OEM"),
                            "fan_type": specs.get("fan_type", "Dual Fan"),
                            "vram": specs.get("vram", "-"),
                            "url": it.get("url", ""),
                            "is_steal_deal": it.get("price", 0) > 0 and it.get("price", 0) <= 3500000
                        })
            except Exception:
                pass

    if not all_deals:
        print("[*] Tidak ada deal untuk disinkronkan.")
        return

    # Kirim ke Supabase REST API (Upsert on URL conflict)
    api_url = f"{SUPABASE_URL}/rest/v1/vga_deals"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(all_deals).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            if resp.status in [200, 201]:
                print(f"[+] Berhasil sinkronisasi {len(all_deals)} listing ke Supabase Cloud!")
    except Exception as e:
        print(f"[-] Gagal sinkronisasi ke Supabase: {e}")

if __name__ == "__main__":
    sync_deals_to_supabase()
