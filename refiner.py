"""
refiner.py — Data Refinery Pipeline: Raw Bronze -> Gold Deals
Baca dari raw_scrapes (refined=false), bersihkan, dan tulis ke gold_deals.

Jalankan manual: python refiner.py
Atau jadwalkan via Windows Task Scheduler / cron.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

from config import (
    SUPABASE_URL, SUPABASE_SERVICE_KEY,
    FLIPPING_TARGETS_SORTED, BANNED_NON_GPU, BANNED_JUNK_BRANDS,
    BANNED_JUNK_MODELS, match_gpu_model, detect_brand, get_cooler_tier,
    STAGE2_RED_FLAGS, STAGE2_GREEN_FLAGS, MIN_PRICE_FLOOR,
)

# ==============================================================================
# KONSTANTA REFINER
# ==============================================================================

# Spotter: kata kunci kondisi fisik
SEAL_KEYWORDS = {
    "REPASTE": ["ganti thermal paste", "ganti pasta", "repaste", "ganti termal", "buka baut segel", "sudah dibuka"],
    "UTUH":    ["segel utuh", "belum pernah bongkar", "masih segel", "baru dibeli"],
    "PERNAH_BUKA": ["pernah bongkar", "bekas bongkaran", "baut segel jebol"],
}

BOX_KEYWORDS = {
    "FULLSET": ["fullset", "full set", "dus lengkap", "kotak lengkap", "komplit", "lengkap"],
    "DUS_POLOS": ["dus polos", "dus doang", "box doang", "box polos"],
    "NO_DUS":  ["no dus", "tanpa dus", "tanpa box", "no box", "gak ada dus"],
}

USAGE_KEYWORDS = {
    "PRIBADI":  ["pemakaian pribadi", "pribadi", "personal use", "buat gaming", "gaming doang", "gaming tipis"],
    "MINING":   ["bekas mining", "ex mining", "mining", "kena mining"],
    "GAMING":   ["gaming", "render", "editing"],
}

FLAW_KEYWORDS = {
    "KARAT":  ["karat", "korosi", "berkarat", "rusty", "korosif", "berjamur"],
    "KOTOR":  ["kotor parah", "berdebu tebal", "debu tebal", "sangat kotor"],
    "PATAH":  ["patah", "retak", "pecah", "bracket patah", "pcb patah"],
}

NEGO_KEYWORDS = ["nego", "negotiable", "bisa nego", "open price", "op ", "harga terbuka", "terbuka"]

# ==============================================================================
# REGEX ENGINE
# ==============================================================================

def _find_keyword(text: str, keyword_map: dict) -> str:
    t = text.lower()
    for label, kws in keyword_map.items():
        if any(kw in t for kw in kws):
            return label
    return "UNKNOWN"


def refine_listing(raw: dict) -> dict | None:
    """
    Proses satu listing mentah jadi data gold.
    Return None jika listing harus di-reject.
    """
    title = raw.get("title", "")
    desc = raw.get("description", "")
    price = raw.get("price", 0)
    full_text = (title + " " + desc).lower()

    # =========================================================================
    # TAHAP 1 — REJECT RULES (Hard Reject)
    # =========================================================================

    # Reject non-GPU / barang sampah / brand rekondisi
    if any(b in full_text for b in BANNED_NON_GPU):
        return {"gold_status": "REJECTED_JUNK", "reject_reason": "Non-GPU / PC rakitan / aksesori"}
    if any(b in full_text for b in BANNED_JUNK_BRANDS):
        return {"gold_status": "REJECTED_JUNK", "reject_reason": "Brand chip rekondisi Cina"}
    if any(b in full_text for b in BANNED_JUNK_MODELS):
        return {"gold_status": "REJECTED_LOW_SPEC", "reject_reason": "Spesifikasi GPU di bawah threshold"}

    # Reject toko suspend / tutup / toko libur / akun dibekukan (kasus Toco & Marketplace)
    SHOP_INACTIVE_FLAGS = ["toko libur", "toko tutup", "toko ditutup", "toko disuspend", "akun ditangguhkan", "akun dibekukan", "seller suspended", "sedang libur", "tidak aktif"]
    if any(flag in full_text for flag in SHOP_INACTIVE_FLAGS):
        return {"gold_status": "REJECTED_JUNK", "reject_reason": "Toko/Seller sedang libur atau kena suspend"}

    # Reject GPU di bawah spec minimum
    chipset = match_gpu_model(title) or match_gpu_model(desc)
    if not chipset:
        return {"gold_status": "REJECTED_JUNK", "reject_reason": "Model GPU tidak dikenali"}

    # =========================================================================
    # TAHAP 2 — EKSTRAKSI SPESIFIKASI
    # =========================================================================

    brand = detect_brand(title)
    tier_name, tier_mult, tier_bonus = get_cooler_tier(title + " " + desc)

    cooler_map = {"S+": "Premium Flagship", "S": "Premium", "A": "Standard", "B": "Entry / Single Fan"}
    cooler_type = cooler_map.get(tier_name, "Standard")

    # Ekstrak VRAM dari teks
    vram_match = re.search(r"(\d+)\s*gb", full_text)
    vram = f"{vram_match.group(1)}GB" if vram_match else "-"

    # =========================================================================
    # TAHAP 3 — TAGGING KONDISI
    # =========================================================================

    is_negotiable = any(kw in full_text for kw in NEGO_KEYWORDS)
    box_status   = _find_keyword(full_text, BOX_KEYWORDS)
    seal_status  = _find_keyword(full_text, SEAL_KEYWORDS)
    usage_claim  = _find_keyword(full_text, USAGE_KEYWORDS)
    physical_flaw = _find_keyword(full_text, FLAW_KEYWORDS)

    # =========================================================================
    # TAHAP 4 — KEPUTUSAN GOLD
    # =========================================================================

    # Hitung skor kelayakan sederhana (bukan ML, murni aturan logika)
    score = 50  # baseline

    # Bonus kondisi positif
    if box_status == "FULLSET": score += 10
    if seal_status == "UTUH": score += 15
    if usage_claim == "PRIBADI": score += 10
    if is_negotiable: score += 5

    # Penalti kondisi negatif
    if usage_claim == "MINING": score -= 20
    if physical_flaw != "NONE" and physical_flaw != "UNKNOWN": score -= 20
    if seal_status == "REPASTE": score -= 5
    if tier_name == "B": score -= 10

    # Red/Green flags deskripsi
    for red in STAGE2_RED_FLAGS:
        if red in full_text:
            score -= 15
    for green in STAGE2_GREEN_FLAGS:
        if green in full_text:
            score += 8

    score = max(0, min(100, score))

    # Tentukan gold_status final
    if physical_flaw not in ("NONE", "UNKNOWN"):
        gold_status = "WARNING_FLAW"
        action_note = f"Ada cacat fisik: {physical_flaw}. Tawar sadis atau skip."
    elif usage_claim == "MINING":
        gold_status = "WARNING_FLAW"
        action_note = "Bekas mining. Cek suhu dan stress test saat COD."
    elif score >= 60:
        gold_status = "APPROVED"
        action_note = "Lanjut ke langkah pengecekan harga & penawaran."
    else:
        gold_status = "APPROVED"
        action_note = "Lolos filter dasar. Verifikasi manual sebelum beli."

    # Generate deal hash
    deal_hash = hashlib.md5(f"{title.lower().strip()}_{price}".encode()).hexdigest()

    return {
        "raw_id": raw.get("id"),
        "title": title,
        "price": price,
        "price_raw": raw.get("price_raw", ""),
        "platform": raw.get("platform", ""),
        "location": raw.get("location", "Indonesia"),
        "url": raw.get("url", ""),
        "image_url": raw.get("image_url", ""),
        "chipset": chipset.upper(),
        "brand": brand,
        "variant": "",
        "vram": vram,
        "cooler_type": cooler_type,
        "cooler_tier": tier_name,
        "is_negotiable": is_negotiable,
        "box_status": box_status,
        "seal_status": seal_status,
        "usage_claim": usage_claim,
        "physical_flaw": physical_flaw if physical_flaw != "UNKNOWN" else "NONE",
        "vision_note": "",
        "gold_status": gold_status,
        "reject_reason": "",
        "is_steal_candidate": score >= 65,
        "action_note": action_note,
        "deal_hash": deal_hash,
        "is_steal_deal": score >= 70,
        "smart_score": score,
        "deal_type": "STEAL_DEAL" if score >= 70 else "PENDING",
        "action_decision": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ==============================================================================
# SUPABASE HELPERS
# ==============================================================================

def _supabase_get(path: str) -> list:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _supabase_post(path: str, data: list, prefer: str = "resolution=merge-duplicates"):
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        data=json.dumps(data).encode("utf-8"),
        headers={
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status


def _mark_refined(raw_ids: list[str]):
    """Tandai raw_scrapes sebagai sudah diproses."""
    for raw_id in raw_ids:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/raw_scrapes?id=eq.{raw_id}",
            data=json.dumps({"refined": True}).encode("utf-8"),
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            method="PATCH",
        )
        urllib.request.urlopen(req, timeout=10)


# ==============================================================================
# MAIN REFINER RUNNER
# ==============================================================================

def run_refiner(batch_size: int = 50):
    """Ambil raw_scrapes yang belum diproses, refine, push ke gold_deals."""
    print(f"\n[*] REFINER START — Mengambil raw batch (max {batch_size})...")

    try:
        raw_batch = _supabase_get(
            f"raw_scrapes?refined=eq.false&order=scraped_at.asc&limit={batch_size}&select=*"
        )
    except Exception as e:
        print(f"[-] Gagal ambil raw batch: {e}")
        return

    if not raw_batch:
        print("[*] Tidak ada raw listing baru untuk diproses.")
        return

    print(f"[*] Memproses {len(raw_batch)} listing mentah...")

    gold_rows = []
    rejected_ids = []
    approved_ids = []

    for raw in raw_batch:
        result = refine_listing(raw)
        if result is None:
            rejected_ids.append(raw["id"])
            continue

        if result.get("gold_status", "").startswith("REJECTED"):
            rejected_ids.append(raw["id"])
            print(f"  [REJECT] {raw.get('title', '')[:60]} — {result.get('reject_reason', '')}")
        else:
            result["raw_id"] = raw["id"]
            gold_rows.append(result)
            approved_ids.append(raw["id"])

    # Push ke gold_deals (Deduplicate deal_hash di memori batch agar tidak error 21000 di Postgres)
    if gold_rows:
        unique_gold = {}
        for g in gold_rows:
            unique_gold[g["deal_hash"]] = g
        deduped_rows = list(unique_gold.values())

        try:
            _supabase_post("gold_deals?on_conflict=deal_hash", deduped_rows)
            print(f"[+] {len(deduped_rows)} listing -> gold_deals (sukses deduplikasi)")
        except Exception as e:
            if hasattr(e, "read"):
                print(f"[-] Gold push detail: {e.read().decode('utf-8')[:300]}")
            print(f"[-] Gagal push gold: {e}")

    # Discord alert untuk steal candidates
    steal_deals = [g for g in gold_rows if g.get("is_steal_deal")]
    for deal in steal_deals:
        try:
            from hunter import send_discord_alert
            deal["source"] = deal.get("platform", "")
            send_discord_alert(deal, deal_type="STEAL_DEAL", smart_score=deal.get("smart_score", 70))
        except Exception:
            pass

    # Tandai semua raw sebagai refined (baik approved maupun rejected)
    all_processed = approved_ids + rejected_ids
    try:
        _mark_refined(all_processed)
    except Exception as e:
        print(f"[-] Gagal mark refined: {e}")

    print(f"\n[*] REFINER SELESAI:")
    print(f"    - Lolos ke Gold: {len(gold_rows)}")
    print(f"    - Ditolak: {len(rejected_ids)}")
    print(f"    - Steal Candidates: {len(steal_deals)}")


if __name__ == "__main__":
    run_refiner(batch_size=50)
