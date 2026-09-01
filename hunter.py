import asyncio
import json
import re
import sqlite3
import sys
import urllib.request
from scraper import scrape_fb_marketplace
from scraper_tokped import scrape_tokopedia_vga
from scraper_toco import scrape_toco_vga
from sync_supabase import sync_deals_to_supabase
from smart_learner import learner

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1544396122817167523/Ior0SHvrYqGkuCpzU1zz0beB8YJGIzxFeeuHGvR67Hp0HqyCRLMBHT6npGmMWfldKxjK"

# ==============================================================================
# DAFTAR VGA FAST MOVING (LAKU KERAS & CUAN FLIPPING) + TARGET HARGA SNIPER
# Format: model -> (HARGA_LANTAI_WARAS, MAX_HARGA_KULAK_UNTUNG)
# ==============================================================================
FLIPPING_TARGETS = {
    # Nvidia RTX 40 & 30 Series (Fastest Moving)
    "rtx 4060":        (3000000, 3900000),  # Resale normal 4.3jt+
    "rtx 3070":        (3300000, 4300000),  # Resale normal 4.7jt+
    "rtx 3060 ti":     (2800000, 3700000),  # Resale normal 4.1jt+
    "rtx 3060":        (2300000, 3200000),  # Resale normal 3.6jt+
    "rtx 3050":        (1600000, 2100000),  # Resale normal 2.4jt+

    # Nvidia RTX 20 & GTX Series (Budget Favorit)
    "rtx 2060 super":  (1900000, 2400000),  # Resale normal 2.7jt+
    "rtx 2060":        (1600000, 2000000),  # Resale normal 2.3jt+
    "gtx 1660 super":  (1100000, 1450000),  # Resale normal 1.8jt+
    "gtx 1660 ti":     (1200000, 1500000),  # Resale normal 1.8jt+
    "gtx 1660":        (1000000, 1350000),  # Resale normal 1.6jt+
    "gtx 1650 super":  (900000,  1250000),  # Resale normal 1.5jt+

    # AMD Radeon RX 7000 & 6000 Series (High Demand)
    "rx 7600":         (3000000, 4000000),  # Resale normal 4.4jt+
    "rx 6700 xt":      (2600000, 3400000),  # Resale normal 3.9jt+
    "rx 6600 xt":      (2000000, 2500000),  # Resale normal 2.9jt+
    "rx 6600":         (1600000, 2050000),  # Resale normal 2.4jt+
}

# Blacklist VGA Purba / Ampas (Susah Dijual & Margin Receh)
BANNED_JUNK_MODELS = [
    "gt 710", "gt 730", "gt 1030", "gt 210", "gt 610", "gt710", "gt730", "gt1030",
    "gtx 750", "gtx 650", "gtx 950", "gtx 960", "gtx 750ti", "gtx 750 ti",
    "rx 550", "rx 560", "rx 460", "rx 570", "rx 580", "rx580", "rx570", "rx550",
    "r7 240", "r7 250", "r7 370", "r9 380", "r9 390", "hd 7730", "hd 5450"
]

# Blacklist kata kunci rusak / spare part / dus
NEGATIVE_KEYWORDS = [
    "no display", "nodisplay", "no disp", "no signal", "tanpa display",
    "part", "parts", "part -", "bahan", "servis", "service", "kanibal", "kanibalan",
    "dus", "box", "kotak", "hanya box", "box only", "no unit", "empty box",
    "fan", "kipas", "backplate", "bracket", "heatsink", "casing", "cooler",
    "matot", "mati", "rusak", "artefak", "mati total", "kabel", "riser",
    "minus", "error", "blank", "garis", "short", "konslet"
]

# Frasa aman (tidak diblokir)
SAFE_PHRASES = [
    "no minus", "tanpa minus", "non minus", "gak ada minus", "tidak ada minus",
    "no artefak", "tanpa artefak", "bebas artefak", "anti artefak",
    "bukan matot", "bukan kanibal", "bukan bahan", "bukan bekas servis", "tanpa kendala",
    "dijamin aman", "normal jaya", "siap pakai", "tes lancar", "lulus tes"
]

ALERT_UNPRICED = True

def init_db():
    conn = sqlite3.connect("seen_deals.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            url TEXT PRIMARY KEY,
            title TEXT,
            price INTEGER,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def is_deal_seen(url: str) -> bool:
    conn = sqlite3.connect("seen_deals.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM deals WHERE url = ?", (url,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def save_deal(url: str, title: str, price: int, source: str):
    conn = sqlite3.connect("seen_deals.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO deals (url, title, price, source) VALUES (?, ?, ?, ?)",
              (url, title, price, source))
    conn.commit()
    conn.close()

def evaluate_deal(title: str, price: int) -> tuple[bool, str, str]:
    t_clean = title.lower()
    
    # 1. Bersihkan frasa positif
    for safe in SAFE_PHRASES:
        t_clean = t_clean.replace(safe, "")
        
    # 2. Tolak kata kunci rusak / part / dus
    for bad_word in NEGATIVE_KEYWORDS:
        if re.search(r"\b" + re.escape(bad_word) + r"\b", t_clean) or bad_word in t_clean:
            return False, "DIBLOKIR_KATA_KUNCI", f"Mengandung '{bad_word}'"
            
    # 3. Tolak VGA purba/ampas (GT 730, RX 580 bekas mining, GTX 750 Ti)
    for junk in BANNED_JUNK_MODELS:
        if junk in t_clean:
            return False, "VGA_AMPAS", f"Model tidak prospek ({junk})"
            
    # 4. Tangkap postingan Free / Nego jika masuk daftar model incaran
    if price == 0 and ALERT_UNPRICED:
        for model in FLIPPING_TARGETS.keys():
            if model in t_clean:
                return True, "UNPRICED", f"Free/Nego {model.upper()}"
        return False, "FREE_BUKAN_TARGET", "Bukan VGA target flipper"
        
    # 5. Cek apakah masuk Target VGA Fast Moving & Harga Masuk Akal Cuan
    for model, (min_floor, max_snipe) in FLIPPING_TARGETS.items():
        if model in t_clean:
            # Cegah barang matot (di bawah harga lantai)
            if price < min_floor:
                return False, "HARGA_CURIGA_MATOT", f"{model.upper()} harga Rp {price:,} terlalu murah (curiga matot)"
                
            # Cek apakah ada data pasar hasil pembelajaran dinamis
            learned = learner.get_learned_market_stats(model)
            if learned:
                max_snipe = learned["smart_max_kulak"]
                min_floor = learned["smart_min_floor"]
            
            # Harga Rp 0 / minta chat seller
            if price == 0:
                return True, "UNPRICED", f"Harga Rp 0 / Chat Seller ({model.upper()})", 50
                
            # Tolak jika harga di bawah lantai waras
            if price < min_floor:
                return False, "HARGA_CURIGA_RUSAK", f"{model.upper()} Rp {price:,} di bawah harga lantai (Curiga Rusak/Kanibal)", 0
                
            # Lolos jika harga di bawah target kulak
            if price <= max_snipe:
                smart_score = learner.compute_steal_score(title, price, model, max_snipe)
                return True, "STEAL_DEAL", f"Target {model.upper()} (Max Rp {max_snipe:,})", smart_score
            else:
                return False, "HARGA_KEMAHALAN", f"{model.upper()} Rp {price:,} di atas batas kulak Rp {max_snipe:,}", 0
                
    return False, "BUKAN_MODEL_TARGET", "Bukan VGA incaran bisnis", 0

def prune_old_discord_alerts(days: int = 7):
    """Hapus otomatis pesan alert lama di Discord agar channel tetap bersih."""
    if not DISCORD_WEBHOOK_URL:
        return
    conn = sqlite3.connect("seen_deals.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS discord_alerts (
            message_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Cari pesan > 7 hari
    c.execute("SELECT message_id FROM discord_alerts WHERE created_at < datetime('now', ?)", (f"-{days} days",))
    old_msgs = [r[0] for r in c.fetchall()]
    
    base_wh = DISCORD_WEBHOOK_URL.split("?")[0]
    for msg_id in old_msgs:
        try:
            del_url = f"{base_wh}/messages/{msg_id}"
            req = urllib.request.Request(del_url, method="DELETE", headers={"User-Agent": "VGAHunter/1.0"})
            urllib.request.urlopen(req, timeout=5)
            c.execute("DELETE FROM discord_alerts WHERE message_id = ?", (msg_id,))
        except Exception:
            pass
    conn.commit()
    conn.close()

def send_discord_alert(deal: dict, deal_type: str = "STEAL_DEAL", smart_score: int = 80):
    is_unpriced = deal_type == "UNPRICED"
    badge_discord = "⚠️ [TANYA HARGA / FREE]" if is_unpriced else f"💎 [STEAL DEAL • SKOR AI {smart_score}/100]"
    badge_console = "[TANYA HARGA / FREE]" if is_unpriced else f"[STEAL DEAL • SKOR {smart_score}/100]"
    color = 16776960 if is_unpriced else 3066993  # Hijau Toska
    
    source_name = deal["source"].upper().replace("_", " ")
    print(f"\n{badge_console} [{source_name}] {deal['price_raw']} - {deal['title']}")
    print(f"   Link: {deal['url']}")

    if not DISCORD_WEBHOOK_URL:
        return

    payload = {
        "username": "VGA Hunter Sniper",
        "embeds": [{
            "title": f"{badge_discord} {deal['title']}",
            "url": deal["url"],
            "color": color,
            "fields": [
                {"name": "💰 Harga Kulak", "value": f"**{deal['price_raw']}**", "inline": True},
                {"name": "🎯 Skor Kelayakan AI", "value": f"**{smart_score}/100**", "inline": True},
                {"name": "🏪 Platform", "value": f"`{source_name}`", "inline": True},
                {"name": "📍 Lokasi", "value": deal.get("location", "-"), "inline": True},
                {"name": "🔗 Link Listing", "value": f"[Klik Buka & Chat Seller]({deal['url']})", "inline": False},
            ],
            "footer": {"text": "VGA Hunter • Self-Learning Market Intelligence"}
        }]
    }

    try:
        # Gunakan ?wait=true agar Discord mengembalikan message_id untuk auto-prune
        wh_url = f"{DISCORD_WEBHOOK_URL.split('?')[0]}?wait=true"
        req = urllib.request.Request(
            wh_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "VGAHunter/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg_id = data.get("id")
            if msg_id:
                conn = sqlite3.connect("seen_deals.db")
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS discord_alerts (message_id TEXT PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                c.execute("INSERT OR IGNORE INTO discord_alerts (message_id) VALUES (?)", (str(msg_id),))
                conn.commit()
                conn.close()
        print(f"[+] Alert Discord terkirim! (ID: {msg_id})")
    except Exception as e:
        print(f"[-] Discord webhook error: {e}")

async def run_sniper_round():
    init_db()
    queries = [
        "rtx 3060", "rx 6600", "gtx 1660 super",
        "rtx 2060", "rtx 3070", "rx 6700 xt", "rtx 4060", "rx 7600"
    ]
    all_deals = []

    print("\n" + "="*50)
    print(f"[*] MEMULAI SNIPER VGA CUAN (Hanya VGA Fast Moving)")
    print("="*50)

    for q in queries:
        print(f"\n[*] Scan Query: '{q}'")
        # 1. Tokopedia
        try:
            tokped_results = await scrape_tokopedia_vga(query=q, min_price=1000000, max_price=5000000, max_items=15)
            all_deals.extend(tokped_results)
        except Exception as e:
            print(f"[-] Tokopedia error: {e}")

        # 2. FB Marketplace
        try:
            fb_results = await scrape_fb_marketplace(query=q, city="jakarta", min_price=0, max_price=5000000, days_since_listed=7, max_items=15)
            all_deals.extend(fb_results)
        except Exception as e:
            print(f"[-] FB error: {e}")

        # 3. Toco.id
        try:
            toco_results = await scrape_toco_vga(query=q, min_price=1000000, max_price=5000000, max_items=15)
            all_deals.extend(toco_results)
        except Exception as e:
            print(f"[-] Toco error: {e}")

    # Evaluasi & Alert
    new_alerts = 0
    already_seen_count = 0
    junk_blocked_count = 0
    overprice_count = 0

    for deal in all_deals:
        url = deal["url"]
        if is_deal_seen(url):
            already_seen_count += 1
            continue

        save_deal(url, deal["title"], deal["price"], deal["source"])

        should_alert, deal_type, reason, smart_score = evaluate_deal(deal["title"], deal["price"])
        
        # Rekam sampel data ke modul pembelajaran statistik (Self-Learning Memory)
        model_matched = None
        for m in FLIPPING_TARGETS:
            if m in deal["title"].lower():
                model_matched = m
                break
        if model_matched:
            learner.record_deal_sample(model_matched, deal["price"], deal["source"], deal["title"], should_alert)

        if should_alert:
            send_discord_alert(deal, deal_type=deal_type, smart_score=smart_score)
            new_alerts += 1
            await asyncio.sleep(0.4)
        else:
            if "AMPAS" in deal_type or "DIBLOKIR" in deal_type or "RUSAK" in deal_type:
                junk_blocked_count += 1
            elif "KEMAHALAN" in deal_type:
                overprice_count += 1

    print("\n" + "="*50)
    print(f"[*] RINGKASAN PEMINDAIAN SNIPER:")
    print(f"[*] Total valid deals ditemukan: {len(all_deals)}")
    
    # Sinkronisasi ke Supabase Cloud
    try:
        sync_deals_to_supabase()
    except Exception as e:
        print(f"[-] Supabase sync error: {e}")
        
    # Auto-Prune alert Discord lama (> 7 hari)
    try:
        prune_old_discord_alerts(days=7)
    except Exception as e:
        print(f"[-] Discord prune error: {e}")
        
    print(f"    - Listing lama dilewati: {already_seen_count}")
    print(f"    - Diblokir (VGA ampas/matot/dus): {junk_blocked_count}")
    print(f"    - Dilewati (Harga kemahalan/gak ada margin): {overprice_count}")
    print(f"    - ALERT CUAN TERKIRIM KE DISCORD: {new_alerts}")
    print("="*50)

from datetime import datetime
from sync_supabase import SUPABASE_URL, SUPABASE_SERVICE_KEY

def get_remote_command() -> dict:
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/bot_commands?id=eq.main&select=command,state",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                return data[0]
    except Exception:
        pass
    return {"command": "RESUME", "state": "IDLE"}

def update_bot_state(state: str, reset_command: bool = False):
    try:
        payload = {"state": state, "last_ping": datetime.utcnow().isoformat() + "Z"}
        if reset_command:
            payload["command"] = "RESUME"
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/bot_commands?id=eq.main",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            },
            method="PATCH"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

async def main_loop(interval_minutes: int = 10):
    print(f"[*] VGA Hunter cloud-controlled loop aktif (Cek tiap {interval_minutes} menit / kendali web)")
    while True:
        remote = get_remote_command()
        cmd = remote.get("command", "RESUME")
        
        if cmd == "STOP":
            print("[!] Menerima perintah STOP dari Web. Mematikan bot...")
            update_bot_state("OFFLINE")
            break
            
        if cmd == "PAUSE":
            update_bot_state("PAUSED")
            await asyncio.sleep(5)
            continue
            
        update_bot_state("SCANNING", reset_command=(cmd == "SCAN_NOW"))
        try:
            await run_sniper_round()
        except Exception as e:
            print(f"[-] Round error: {e}")
            
        update_bot_state("IDLE")
        
        # Sleep dengan respon instan jika ada perintah dari Web
        total_seconds = interval_minutes * 60
        elapsed = 0
        while elapsed < total_seconds:
            await asyncio.sleep(5)
            elapsed += 5
            check = get_remote_command()
            if check.get("command") in ["SCAN_NOW", "PAUSE", "STOP"]:
                break

if __name__ == "__main__":
    if "--reset-db" in sys.argv:
        conn = sqlite3.connect("seen_deals.db")
        conn.cursor().execute("DELETE FROM deals")
        conn.commit()
        conn.close()
        print("[*] Database seen_deals.db di-reset!")
        
    if "--once" in sys.argv:
        asyncio.run(run_sniper_round())
    else:
        asyncio.run(main_loop(interval_minutes=10))
