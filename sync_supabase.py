import json
import os
import urllib.request
import urllib.parse

# KONFIGURASI SUPABASE LIVE
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://bgsmqeglwfjmkxbvbeay.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJnc21xZWdsd2ZqbWt4YnZiZWF5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyNzk3ODEsImV4cCI6MjEwMzg1NTc4MX0.fqdvKhXuXgfZYqu-M2yJrNgLla7B-8xdC3Vht_uEBVY")


def parse_gpu_specs(title):
    t = title.lower()
    
    # 1. Tentukan Brand
    brand = "OEM"
    brands = {"asus": "ASUS", "msi": "MSI", "gigabyte": "GIGABYTE", "zotac": "ZOTAC", "colorful": "COLORFUL", "palit": "PALIT", "galax": "GALAX", "inno3d": "INNO3D", "asrock": "ASROCK", "powercolor": "POWERCOLOR", "sapphire": "SAPPHIRE", "xfx": "XFX", "evga": "EVGA", "pny": "PNY"}
    for k, v in brands.items():
        if k in t:
            brand = v
            break
            
    # 2. Tentukan Tier / Fan
    tier = "Dual Fan (Standard)"
    premium_keys = ["rog", "strix", "suprim", "aorus", "vulcan", "neptune", "gamerock", "amp holo", "ichill", "hof", "taichi", "phantom", "nitro", "toxic", "red devil"]
    triple_keys = ["tuf", "trio", "gaming x trio", "trinity", "steel legend", "hellhound", "merc", "qick", "3 fan", "triple fan"]
    single_keys = ["aero itx", "single fan", "itx", "mini"]
    
    for b in premium_keys:
        if b in t: tier = "Premium Tier"; break
        
    if tier == "Dual Fan (Standard)":
        for b in triple_keys:
            if b in t: tier = "Triple Fan"; break
            
    if tier == "Dual Fan (Standard)":
        for b in single_keys:
            if b in t: tier = "Single Fan / ITX"; break

    # Infer brand if still OEM but has premium tag
    if brand == "OEM":
        if "rog" in t or "strix" in t or "tuf" in t: brand = "ASUS"
        elif "suprim" in t or "trio" in t: brand = "MSI"
        elif "aorus" in t: brand = "GIGABYTE"
        elif "nitro" in t or "toxic" in t: brand = "SAPPHIRE"
        elif "red devil" in t or "hellhound" in t: brand = "POWERCOLOR"

    return {"brand": brand, "fan_type": tier, "vram": "8GB"} # VRAM as default fallback

def sync_deals_to_supabase():
    if "YOUR_PROJECT" in SUPABASE_URL:
        print("[-] Supabase URL / Key belum dikonfigurasi. Lewati sync cloud.")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    files = [os.path.join(base_dir, f) for f in ["tokped_vga_deals.json", "fb_vga_deals.json", "toco_vga_deals.json"]]
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
