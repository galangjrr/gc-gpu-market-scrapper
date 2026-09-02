import json
import urllib.request
from sync_supabase import SUPABASE_URL, SUPABASE_SERVICE_KEY

def check_or_init_bot_commands():
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    
    payload = {
        "id": "main",
        "command": "RESUME",
        "state": "IDLE"
    }
    
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/bot_commands?on_conflict=id",
            data=json.dumps([payload]).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            print("[+] Tabel bot_commands sudah aktif & terhubung di Supabase!")
            return True
    except urllib.error.HTTPError as e:
        print(f"[-] Tabel bot_commands belum ada: {e}")
        return False

if __name__ == "__main__":
    check_or_init_bot_commands()
