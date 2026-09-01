import json
import os
import re
import urllib.request

# BLACKLIST LENGKAP: RUSAK / MATOT / NO DISPLAY / KANIBALAN / NON-GPU
JUNK_BROKEN_KEYWORDS = [
    "no display", "nodisplay", "no disp", "no dp", "matot", "mati total", "mati",
    "artefak", "artifact", "artifak", "garis", "bangkai", "kanibal", "kanibalan",
    "part saja", "part only", "rusak", "servisan", "short", "hangus", "gosong",
    "hanya dus", "box saja", "kotak saja", "dus saja", "cooler only", "heatsink",
    "fan replacement", "kipas saja", "backplate", "bracket", "kabel riser", "riser card",
    "kabel pcie", "dock egpu", "casing egpu", "dummy plug", "converter", "thermal pad",
    "baut", "gt 710", "gt 730", "gt 610", "gt 210", "sepeda", "gunung", "baju", "sepatu",
    "cleat", "motor", "mobil", "kost", "kamar", "rumah", "gundam", "gunpla", "figure"
]

GPU_STRICT_REGEX = re.compile(
    r"\b(?:"
    r"rtx\s*(?:4090|4080|4070|4060|3090|3080|3070|3060|3050|2080|2070|2060)(?:\s*(?:ti|super))?"
    r"|gtx\s*(?:1660|1650|1080|1070|1060|1050)(?:\s*(?:ti|super))?"
    r"|rx\s*(?:7900|7800|7700|7600|6950|6900|6800|6750|6700|6650|6600|6500|5700|5600|5500|590|580|570)(?:\s*xtx|\s*xt)?"
    r"|arc\s*(?:a770|a750|a580|b580|b570)"
    r")\b",
    re.IGNORECASE
)

SUPABASE_URL = "https://bgsmqeglwfjmkxbvbeay.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJnc21xZWdsd2ZqbWt4YnZiZWF5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyNzk3ODEsImV4cCI6MjEwMzg1NTc4MX0.fqdvKhXuXgfZYqu-M2yJrNgLla7B-8xdC3Vht_uEBVY"

def purge_all_junk_from_supabase():
    print("[*] Memeriksa & membasmi VGA rusak / no display / matot dari Supabase...")
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/vga_deals?select=id,title,url,price",
        headers=headers,
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
            
        print(f"[*] Total baris di Supabase: {len(rows)}")
        
        ids_to_delete = []
        for r in rows:
            t = r.get("title", "").lower()
            price = r.get("price", 0)
            
            # 1. Cek keyword rusak/matot/dus/kanibalan
            is_junk = any(j in t for j in JUNK_BROKEN_KEYWORDS)
            
            # 2. Cek apakah GPU valid
            is_valid_gpu = bool(GPU_STRICT_REGEX.search(t))
            
            # 3. Cek batas harga waras
            is_too_cheap = price < 800000
            
            if is_junk or not is_valid_gpu or is_too_cheap:
                ids_to_delete.append(r["id"])
                safe_title = r.get("title", "").encode("ascii", "ignore").decode("ascii")
                print(f"[-] MUSNAHKAN BARANG RUSAK/SAMPAH: {safe_title} (Rp {price:,})")
                
        if ids_to_delete:
            id_list_str = ",".join(ids_to_delete)
            del_req = urllib.request.Request(
                f"{SUPABASE_URL}/rest/v1/vga_deals?id=in.({id_list_str})",
                headers=headers,
                method="DELETE"
            )
            with urllib.request.urlopen(del_req) as del_resp:
                print(f"[+] Sukses menghapus {len(ids_to_delete)} barang rusak dari Supabase Cloud!")
        else:
            print("[+] Database Supabase sudah 100% steril.")
            
    except Exception as e:
        print(f"[-] Error purging Supabase: {e}")

if __name__ == "__main__":
    purge_all_junk_from_supabase()
