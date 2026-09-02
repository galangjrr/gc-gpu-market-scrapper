import json
import os
import urllib.request
import urllib.parse

# KONFIGURASI SUPABASE LIVE
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://bgsmqeglwfjmkxbvbeay.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJnc21xZWdsd2ZqbWt4YnZiZWF5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyNzk3ODEsImV4cCI6MjEwMzg1NTc4MX0.fqdvKhXuXgfZYqu-M2yJrNgLla7B-8xdC3Vht_uEBVY")


def parse_gpu_specs(title):
    t = title.lower()
    brand = "OEM"
    premium = ["rog", "strix", "suprim", "aorus", "vulcan", "neptune", "gamerock", "amp holo", "ichill", "hof", "taichi", "phantom", "sapphire", "nitro", "toxic", "red devil"]
    triple = ["tuf", "gaming x", "gigabyte", "eagle", "windforce", "colorful", "palit", "gamingpro", "zotac", "trinity", "galax", "kfa2", "steel legend", "hellhound", "merc", "swft", "qick", "speedster"]
    single = ["aero itx", "single fan", "itx", "mini"]
    
    tier = "Dual Fan (Standard)"
    for b in premium:
        if b in t: brand = b.upper(); tier = "Premium Tier"; break
    if tier == "Dual Fan (Standard)":
        for b in triple:
            if b in t: brand = b.upper(); tier = "Triple Fan"; break
    if tier == "Dual Fan (Standard)":
        for b in single:
            if b in t: brand = b.upper(); tier = "Single Fan / ITX"; break
    if brand == "OEM":
        brands = ["asus", "msi", "gigabyte", "zotac", "colorful", "palit", "galax", "inno3d", "asrock", "powercolor", "sapphire", "xfx", "evga", "pny"]
        for b in brands:
            if b in t: brand = b.upper(); break
            
    return {"brand": brand, "fan_type": tier, "vram": "8GB"} # VRAM as default fallback

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
                            "fan_type": specs.get("fan_type", "Dual Fan (2 Fan)"),
                            "vram": specs.get("vram", "-"),
                            "image_url": it.get("image_url", ""),
                            "url": it["url"],
                            "is_steal_deal": it.get("price", 0) > 0 and it.get("price", 0) <= 3500000
                        })
            except Exception:
                pass

    if not all_deals:
        print("[*] Tidak ada deal untuk disinkronkan.")
        return

    # Kirim ke Supabase REST API (Upsert on URL conflict)
    api_url = f"{SUPABASE_URL}/rest/v1/vga_deals?on_conflict=url"
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
