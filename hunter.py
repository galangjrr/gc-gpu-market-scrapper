import asyncio
import json
import os
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime

from config import (
    BASE_DIR, DB_PATH,
    SUPABASE_URL, SUPABASE_SERVICE_KEY, DISCORD_WEBHOOK_URL,
    FLIPPING_TARGETS, FLIPPING_TARGETS_SORTED,
    BANNED_JUNK_BRANDS, BANNED_JUNK_MODELS, BANNED_NON_GPU, BANNED_NEW_ITEMS,
    SAFE_PHRASES, COOLER_TIERS, MIN_PRICE_FLOOR,
    SEARCH_QUERIES, ALERT_UNPRICED,
    get_cooler_tier, detect_brand, match_gpu_model, is_title_clean,
)
from scrapers import BrowserManager
from scrapers.facebook import scrape_fb_marketplace
from scrapers.tokped import scrape_tokopedia_vga
from scrapers.toco import scrape_toco_vga
from sync_supabase import sync_deals_to_supabase
from dump_raw import dump_raw_to_supabase
from refiner import run_refiner
from smart_learner import learner


# ==============================================================================
# DATABASE LOKAL (SQLite seen_deals)
# ==============================================================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM deals WHERE url = ?", (url,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def save_deal(url: str, title: str, price: int, source: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO deals (url, title, price, source) VALUES (?, ?, ?, ?)",
              (url, title, price, source))
    conn.commit()
    conn.close()


# ==============================================================================
# EVALUASI DEAL
# ==============================================================================

def evaluate_deal_stage1(title: str, price: int, source: str = "") -> tuple[bool, str, str, int, bool]:
    """Evaluasi Stage 1 (Fast Scan): return (should_alert, deal_type, reason, score, needs_stage2)."""

    if not is_title_clean(title):
        return False, "DIBLOKIR_KATA_KUNCI", "Mengandung kata kunci terlarang", 0, False

    model = match_gpu_model(title)
    is_fb = "facebook" in source.lower()

    if not model:
        # PENGECUALIAN FB MARKETPLACE: Judul kaku/malas. Lempar ke Stage 2 (Mystery GPU)
        # Harga wajar ATAU harga troll (0 - 10jt) tetap dibuka deskripsinya.
        if is_fb and price <= 10000000:
            return False, "PENDING_STAGE2_MYSTERY", "Mystery GPU FB (Cari model di deskripsi)", 50, True
        return False, "BUKAN_MODEL_TARGET", "Bukan VGA incaran bisnis", 0, False

    # Jika harga Troll/Unpriced, selalu cek deskripsi (Stage 2) agar tidak kejebak barang rusak/minus
    if price == 0 and ALERT_UNPRICED:
        return False, "PENDING_STAGE2_UNPRICED", f"Free/Nego {model.upper()} (Cek Deskripsi)", 50, True
        
    if 0 < price < MIN_PRICE_FLOOR:
        if is_fb:
            return False, "PENDING_STAGE2_UNPRICED", f"Harga Troll FB {model.upper()} (Cek Deskripsi)", 50, True
        return False, "HARGA_PANCINGAN", f"Rp {price:,} di bawah lantai Rp {MIN_PRICE_FLOOR:,}", 0, False

    min_floor, max_snipe = FLIPPING_TARGETS[model]
    tier_name, tier_mult, tier_bonus = get_cooler_tier(title)

    learned = learner.get_learned_market_stats(model, title)
    if learned:
        max_snipe = learned["smart_max_kulak"]
        min_floor = learned["smart_min_floor"]

    max_snipe = int(max_snipe * tier_mult)
    min_floor = int(min_floor * tier_mult)

    if price < min_floor:
        return False, "HARGA_CURIGA_MATOT", f"{model.upper()} Rp {price:,} terlalu murah (curiga matot)", 0, False

    if price <= max_snipe:
        smart_score = learner.compute_steal_score(title, price, model, max_snipe)
        smart_score = min(100, max(0, smart_score + tier_bonus))
        tier_tag = f" [{tier_name}]" if tier_name != "A" else ""
        return False, "PENDING_STAGE2", f"Target {model.upper()}{tier_tag} (Menunggu Stage 2)", smart_score, True

    return False, "HARGA_KEMAHALAN", f"{model.upper()} Rp {price:,} di atas batas kulak Rp {max_snipe:,}", 0, False


def evaluate_deal_stage2(deal: dict, desc: str, base_score: int) -> tuple[bool, str, str, int]:
    """Evaluasi Stage 2 (Deep Scan): Deteksi NLP Regex ringan pada teks deskripsi."""
    title = deal["title"]
    price = deal["price"]
    source = deal.get("source", "")
    is_fb = "facebook" in source.lower()
    
    model = match_gpu_model(title)
    
    # 1. Pastikan bukan bot jebakan / troll kosong
    if len(desc) < 10:
        return True, "STEAL_DEAL_NO_DESC", f"{model.upper() if model else 'VGA'} (Deskripsi terlalu pendek)", max(0, base_score - 10)

    # 2. MYSTERY GPU RESOLUTION (Model gak ada di judul)
    is_unpriced_troll = (price == 0 or (0 < price < MIN_PRICE_FLOOR and is_fb))
    
    if not model:
        model = match_gpu_model(desc)
        if not model:
            return False, "DIBLOKIR_STAGE2", "Model VGA tetap tidak ditemukan di deskripsi", 0
            
        if not is_unpriced_troll:
            # Evaluasi ulang harga normal karena model baru ketemu
            min_floor, max_snipe = FLIPPING_TARGETS[model]
            tier_name, tier_mult, tier_bonus = get_cooler_tier(desc)
            
            learned = learner.get_learned_market_stats(model, desc)
            if learned:
                max_snipe = learned["smart_max_kulak"]
                min_floor = learned["smart_min_floor"]
                
            max_snipe = int(max_snipe * tier_mult)
            min_floor = int(min_floor * tier_mult)
            
            if price < min_floor: return False, "HARGA_CURIGA_MATOT", f"{model.upper()} Rp {price:,} curiga matot (dari deskripsi)", 0
            if price > max_snipe: return False, "HARGA_KEMAHALAN", f"{model.upper()} Rp {price:,} kemahalan (dari deskripsi)", 0
                
            base_score = learner.compute_steal_score(title + " " + desc, price, model, max_snipe)
            base_score = min(100, max(0, base_score + tier_bonus))

    d_low = desc.lower()
    
    # 3. Cek Red Flags (Minus, Artefak)
    from config import STAGE2_RED_FLAGS, STAGE2_GREEN_FLAGS
    for red in STAGE2_RED_FLAGS:
        if red in d_low:
            return False, "DIBLOKIR_STAGE2", f"Terdeteksi minus di deskripsi: '{red}'", 0
            
    # 4. Hitung Semantic Score (Green Flags)
    score_bonus = 0
    for green in STAGE2_GREEN_FLAGS:
        if green in d_low:
            score_bonus += 10
            
    final_score = min(100, base_score + score_bonus)
    
    # 5. Fuzzy Tier Detection
    tier_name, tier_mult, tier_bonus = get_cooler_tier(desc)
    tier_tag = f" [{tier_name}]" if tier_name != "A" else ""
    
    # 6. Finalisasi Tipe Deal
    if is_unpriced_troll:
        return True, "UNPRICED", f"Harga Troll FB {model.upper()}{tier_tag} (Cek Detail DM)", final_score
        
    return True, "STEAL_DEAL", f"Target {model.upper()}{tier_tag} (Lolos Stage 2)", final_score


# ==============================================================================
# DISCORD ALERT
# ==============================================================================

def prune_old_discord_alerts(days: int = 7):
    """Hapus otomatis pesan alert lama di Discord agar channel tetap bersih."""
    if not DISCORD_WEBHOOK_URL:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS discord_alerts (
            message_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
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
    color = 16776960 if is_unpriced else 3066993

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
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS discord_alerts (message_id TEXT PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                c.execute("INSERT OR IGNORE INTO discord_alerts (message_id) VALUES (?)", (str(msg_id),))
                conn.commit()
                conn.close()
        print(f"[+] Alert Discord terkirim! (ID: {msg_id})")
    except Exception as e:
        print(f"[-] Discord webhook error: {e}")


# ==============================================================================
# SNIPER ROUND — Core scan loop
# ==============================================================================

async def run_sniper_round(custom_queries: list = None, target_platforms: list = None, spotter_config: dict = None):
    init_db()
    all_deals = []

    active_queries = custom_queries if custom_queries else SEARCH_QUERIES
    active_plats = [p.lower() for p in target_platforms] if target_platforms else ["tokopedia", "facebook", "toco"]

    # Batas harga dari spotter_config (default sangat lebar, gak reject data)
    cfg_min = spotter_config.get("min_price", 500000) if spotter_config else 500000
    cfg_max = spotter_config.get("max_price", 30000000) if spotter_config else 30000000

    print("\n" + "=" * 50)
    print(f"[*] MEMULAI RAW INGEST (Platform: {active_plats})")
    print(f"[*] Filter harga: Rp {cfg_min:,} - Rp {cfg_max:,}")
    print("=" * 50)

    manager = BrowserManager()
    await manager.start()

    try:
        for q in active_queries:
            print(f"\n[*] Scan Query: '{q}'")

            tasks = []
            contexts = []
            platform_names = []

            if "tokopedia" in active_plats:
                ctx, page = await manager.new_context()
                contexts.append(ctx)
                tasks.append(scrape_tokopedia_vga(page, query=q, min_price=cfg_min, max_price=cfg_max, max_items=15))
                platform_names.append("Tokopedia")

            if "facebook" in active_plats:
                ctx, page = await manager.new_context(extra_http_headers={"Accept-Language": "id-ID"})
                contexts.append(ctx)
                tasks.append(scrape_fb_marketplace(page, query=q, city="jakarta", min_price=0, max_price=cfg_max, days_since_listed=7, max_items=15))
                platform_names.append("FB")

            if "toco" in active_plats:
                ctx, page = await manager.new_context()
                contexts.append(ctx)
                tasks.append(scrape_toco_vga(page, query=q, min_price=cfg_min, max_price=cfg_max, max_items=15))
                platform_names.append("Toco")

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for ctx in contexts:
                await ctx.close()

            for i, (name, res) in enumerate(zip(platform_names, results)):
                if isinstance(res, list):
                    all_deals.extend(res)
                    print(f"[+] {name}: {len(res)} listing mentah ditangkap")
                else:
                    print(f"[-] {name} error: {res}")

        # Ambil deskripsi untuk listing yang butuh deep scan
        from scrapers import fetch_item_description
        ctx_s2, page_s2 = await manager.new_context()
        for deal in all_deals:
            if is_deal_seen(deal["url"]):
                continue
            save_deal(deal["url"], deal["title"], deal["price"], deal["source"])
            # Fetch deskripsi langsung saat scraping, simpan ke field desc
            try:
                desc = await fetch_item_description(page_s2, deal["url"])
                deal["description"] = desc
            except Exception:
                deal["description"] = ""
        await ctx_s2.close()

    finally:
        await manager.close()

    # Dump semua ke raw_scrapes Supabase (Bronze Layer)
    new_raw = [d for d in all_deals if d.get("url")]
    print(f"\n[*] TOTAL LISTING MENTAH DITANGKAP: {len(new_raw)}")
    try:
        if new_raw:
            dump_raw_to_supabase(new_raw)
    except Exception as e:
        print(f"[-] Raw dump error: {e}")

    # AUTO-CHAIN REFINER: Langsung murnikan data mentah jadi gold_deals
    try:
        print(f"\n[*] MEMICU AUTO-REFINER (Bronze -> Gold, Target: {active_queries})...")
        run_refiner(batch_size=100, custom_queries=active_queries if custom_queries else None)
    except Exception as e:
        print(f"[-] Auto-refiner error: {e}")

    # Auto-Prune Discord alert lama (>7 hari)
    try:
        prune_old_discord_alerts(days=7)
    except Exception:
        pass

    print("=" * 50)




# ==============================================================================
# BOT REMOTE CONTROL (Supabase bot_commands)
# ==============================================================================

def get_remote_command() -> dict:
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/bot_commands?id=eq.main&select=command,state,custom_queries,target_platforms",
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

_current_bot_state = "IDLE"

async def heartbeat_worker():
    """Background heartbeat: kirim ping ke Supabase tiap 20 detik."""
    global _current_bot_state
    while True:
        try:
            update_bot_state(_current_bot_state)
        except Exception:
            pass
        await asyncio.sleep(20)

async def main_loop(interval_minutes: int = 10):
    global _current_bot_state
    print(f"[*] VGA Hunter aktif — Mode: STANDBY. Menunggu perintah SCAN_NOW dari web...")

    asyncio.create_task(heartbeat_worker())

    # Boot dalam STANDBY, bukan langsung scan
    _current_bot_state = "STANDBY"
    update_bot_state("STANDBY")

    while True:
        try:
            remote = get_remote_command()
            cmd = remote.get("command", "STANDBY")

            if cmd == "STOP":
                print("[!] Menerima perintah STOP dari Web. Mematikan bot...")
                _current_bot_state = "OFFLINE"
                update_bot_state("OFFLINE")
                break

            if cmd == "PAUSE":
                _current_bot_state = "PAUSED"
                update_bot_state("PAUSED")
                await asyncio.sleep(5)
                continue

            # Hanya jalankan scan jika ada perintah eksplisit SCAN_NOW
            if cmd == "SCAN_NOW":
                _current_bot_state = "SCANNING"
                update_bot_state("SCANNING", reset_command=True)
                try:
                    c_queries = remote.get("custom_queries")
                    c_plats = remote.get("target_platforms")
                    c_spotter = remote.get("spotter_config")
                    await run_sniper_round(
                        custom_queries=c_queries,
                        target_platforms=c_plats,
                        spotter_config=c_spotter
                    )
                except Exception as e:
                    print(f"[-] Round error: {e}")

                _current_bot_state = "STANDBY"
                update_bot_state("STANDBY")
            else:
                # STANDBY / RESUME / IDLE: diam, polling setiap 5 detik
                _current_bot_state = "STANDBY"
                await asyncio.sleep(5)

        except Exception as err:
            print(f"[!] Loop exception: {err}. Melanjutkan dalam 10 detik...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    if "--reset-db" in sys.argv:
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute("DELETE FROM deals")
        conn.commit()
        conn.close()
        print("[*] Database seen_deals.db di-reset!")

    try:
        if "--once" in sys.argv:
            asyncio.run(run_sniper_round())
        else:
            asyncio.run(main_loop(interval_minutes=10))
    finally:
        update_bot_state("OFFLINE")
        print("[*] Bot dimatikan (OFFLINE).")
