import json
import os
import re
import urllib.request
from scraper_toco import GPU_STRICT_REGEX, BANNED_NON_GPU
from sync_supabase import SUPABASE_URL, SUPABASE_SERVICE_KEY, sync_deals_to_supabase

def purge_garbage_from_supabase():
    print("[*] Membersihkan item sampah/non-GPU dari database Supabase...")
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    # 1. Ambil semua baris di Supabase
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/vga_deals?select=id,title,url",
        headers=headers,
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
            
        print(f"[*] Total baris di Supabase saat ini: {len(rows)}")
        
        ids_to_delete = []
        for r in rows:
            t = r.get("title", "").lower()
            is_banned = any(b in t for b in BANNED_NON_GPU)
            is_valid_gpu = bool(GPU_STRICT_REGEX.search(t))
            
            if is_banned or not is_valid_gpu:
                ids_to_delete.append(r["id"])
                safe_title = r.get("title", "").encode("ascii", "ignore").decode("ascii")
                print(f"[-] Menghapus item non-GPU: {safe_title}")
                
        if ids_to_delete:
            id_list_str = ",".join(ids_to_delete)
            del_req = urllib.request.Request(
                f"{SUPABASE_URL}/rest/v1/vga_deals?id=in.({id_list_str})",
                headers=headers,
                method="DELETE"
            )
            with urllib.request.urlopen(del_req) as del_resp:
                print(f"[+] Sukses menghapus {len(ids_to_delete)} item sampah dari Supabase Cloud!")
        else:
            print("[+] Database Supabase sudah bersih dari item sampah.")
            
    except Exception as e:
        print(f"[-] Error purging Supabase: {e}")

if __name__ == "__main__":
    purge_garbage_from_supabase()
