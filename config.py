"""
config.py — Single Source of Truth untuk VGA Hunter Bot.
Semua konstanta, regex, blacklist, tier, dan secrets terpusat di sini.
"""
import os
import re
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "seen_deals.db")

# Load .env file automatically
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ==============================================================================
# SECRETS (dari .env atau fallback hardcoded sementara)
# ==============================================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://bgsmqeglwfjmkxbvbeay.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJnc21xZWdsd2ZqbWt4YnZiZWF5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyNzk3ODEsImV4cCI6MjEwMzg1NTc4MX0.fqdvKhXuXgfZYqu-M2yJrNgLla7B-8xdC3Vht_uEBVY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1544396122817167523/Ior0SHvrYqGkuCpzU1zz0beB8YJGIzxFeeuHGvR67Hp0HqyCRLMBHT6npGmMWfldKxjK")

# ==============================================================================
# GPU REGEX — Menangkap HANYA model GPU resmi (bukan Gundam RX-78 dll)
# Sesuai gpu_scraper.md: NVIDIA RTX 2060+ dan AMD RX 6600 XT+
# ==============================================================================
GPU_ALLOWED_REGEX = re.compile(
    r"\b(?:"
    # NVIDIA RTX 20/30/40 series (Minimum RTX 2060)
    r"rtx\s*(?:4090|4080(?:\s*super)?|4070(?:\s*(?:ti(?:\s*super)?|super))?|4060(?:\s*ti)?)"
    r"|rtx\s*(?:3090(?:\s*ti)?|3080(?:\s*ti)?|3070(?:\s*ti)?|3060(?:\s*ti)?|3050)"
    r"|rtx\s*(?:2080(?:\s*(?:ti|super))?|2070(?:\s*super)?|2060(?:\s*super)?)"
    # AMD RDNA (Termasuk RX 5600 & RX 6600 Non-XT)
    r"|rx\s*(?:7900\s*xtx|7900\s*xt|7800\s*xt|7700\s*xt|7600(?:\s*xt)?)"
    r"|rx\s*(?:6950\s*xt|6900\s*xt|6800(?:\s*xt)?|6750\s*xt|6700(?:\s*xt)?|6650\s*xt|6600(?:\s*xt)?|5600(?:\s*xt)?)"
    r")\b",
    re.IGNORECASE
)

# Regex lebih longgar untuk FB Marketplace (menangkap juga GTX/low-end supaya bisa di-reject oleh evaluator)
GPU_SEARCH_REGEX = re.compile(
    r"\b(?:"
    r"rtx\s*\d{4}(?:\s*(?:ti|super))?"
    r"|gtx\s*\d{3,4}(?:\s*(?:ti|super))?"
    r"|rx\s*\d{4}(?:\s*(?:xtx|xt))?"
    r"|geforce\s*(?:rtx|gtx)"
    r"|radeon\s*rx"
    r")\b",
    re.IGNORECASE
)

# ==============================================================================
# FLIPPING TARGETS — Harga Kulak Baseline (Sesuai gpu_scraper.md: RTX 2060+ / RX 6600 XT+)
# Format: model -> (HARGA_LANTAI_WARAS, MAX_HARGA_KULAK_UNTUNG)
# GTX 10xx, GTX 16xx, RX 5xxx, RX 6600 non-XT DIHAPUS dari sini.
# ==============================================================================
FLIPPING_TARGETS = {
    # Ada Lovelace (RTX 40)
    "rtx 4090":        (12000000, 16000000),
    "rtx 4080 super":  (8500000, 11000000),
    "rtx 4080":        (7500000, 10000000),
    "rtx 4070 ti super": (6500000, 8500000),
    "rtx 4070 ti":     (5500000, 7500000),
    "rtx 4070 super":  (5000000, 6500000),
    "rtx 4070":        (4500000, 6000000),
    "rtx 4060 ti":     (3800000, 4800000),
    "rtx 4060":        (3000000, 3900000),
    # Ampere (RTX 30)
    "rtx 3090 ti":     (6000000, 8000000),
    "rtx 3090":        (5500000, 7500000),
    "rtx 3080 ti":     (4500000, 6000000),
    "rtx 3080":        (4000000, 5500000),
    "rtx 3070 ti":     (3500000, 4500000),
    "rtx 3070":        (3300000, 4300000),
    "rtx 3060 ti":     (2800000, 3700000),
    "rtx 3060":        (2300000, 3200000),
    "rtx 3050":        (1600000, 2100000),
    # Turing (RTX 20)
    "rtx 2080 ti":     (3000000, 4000000),
    "rtx 2080 super":  (2500000, 3200000),
    "rtx 2080":        (2200000, 2800000),
    "rtx 2070 super":  (2000000, 2600000),
    "rtx 2070":        (1800000, 2300000),
    "rtx 2060 super":  (1900000, 2400000),
    "rtx 2060":        (1600000, 2000000),
    # AMD RDNA 3
    "rx 7900 xtx":     (7000000, 9500000),
    "rx 7900 xt":      (5500000, 7500000),
    "rx 7800 xt":      (4000000, 5500000),
    "rx 7700 xt":      (3500000, 4500000),
    "rx 7600 xt":      (3000000, 3800000),
    "rx 7600":         (2800000, 3500000),
    # AMD RDNA 2 (Minimum RX 6600 XT)
    "rx 6950 xt":      (4000000, 5500000),
    "rx 6900 xt":      (3500000, 5000000),
    "rx 6800 xt":      (3200000, 4200000),
    "rx 6800":         (2800000, 3800000),
    "rx 6750 xt":      (3400000, 4200000),
    "rx 6700 xt":      (3200000, 3800000),
    "rx 6700":         (2500000, 3200000),
    "rx 6650 xt":      (2200000, 3000000),
    "rx 6600 xt":      (2000000, 2800000),
    "rx 6600":         (1700000, 2400000),
    "rx 5600 xt":      (1100000, 1500000),
    "rx 5600":         (1000000, 1400000),
}

# Urutan lookup: model panjang dulu agar "rtx 4070 ti super" match sebelum "rtx 4070 ti"
FLIPPING_TARGETS_SORTED = sorted(FLIPPING_TARGETS.keys(), key=len, reverse=True)

# ==============================================================================
# BLACKLISTS — Semua brand, model, dan keyword yang WAJIB ditolak
# ==============================================================================

# Brand daur ulang chip mining / rekondisi Cina (TOLAK MUTLAK)
BANNED_JUNK_BRANDS = [
    "aisurix", "mllse", "peladn", "soyo", "jieshuo", "szmz",
    "51risc", "veinida", "arktek", "venomrx", "buldozer", "varro",
    "imperion", "inforce", "kllisre", "afox", "bulldozer"
]

# Model GPU purba / ampas (di bawah minimum spec)
BANNED_JUNK_MODELS = [
    "gt 210", "gt 610", "gt 710", "gt 730", "gt 1030",
    "gtx 750", "gtx 750 ti", "gtx 950", "gtx 960",
    "gtx 1050", "gtx 1050 ti", "gtx 1060", "gtx 1070", "gtx 1070 ti",
    "gtx 1080", "gtx 1080 ti",
    "gtx 1650", "gtx 1650 super", "gtx 1660", "gtx 1660 super", "gtx 1660 ti",
    "rx 460", "rx 470", "rx 480", "rx 550", "rx 560", "rx 570", "rx 580", "rx 590",
    "rx 5500 xt", "rx 5700", "rx 5700 xt",
    "rx 6400", "rx 6500 xt",
]

# Keyword non-GPU (sepeda, gundam, properti, PC rakitan, laptop, sparepart)
BANNED_NON_GPU = [
    # Barang rusak / matot / sparepart
    "no display", "nodisplay", "no disp", "no dp", "no signal", "tanpa display",
    "matot", "mati total", "mati",
    "artefak", "artifact", "artifak", "garis", "bangkai", "kanibal", "kanibalan",
    "part saja", "part only", "part", "parts", "part -", "bahan", "servis", "service",
    "rusak", "servisan", "short", "hangus", "gosong", "konslet", "error", "blank",
    "hanya dus", "box saja", "kotak saja", "dus saja", "dus", "box", "kotak",
    "hanya box", "box only", "no unit", "empty box",
    "cooler only", "heatsink only", "hanya heatsink", "heatsink",
    "fan replacement", "kipas saja", "hanya fan", "fan only", "kipas only",
    "hanya kipas", "fan mati", "kipas mati", "fan rusak", "ganti fan",
    "backplate", "bracket", "kabel riser", "riser card", "riser",
    "kabel pcie", "dock egpu", "casing egpu", "dummy plug", "converter", "thermal pad", "baut",
    "casing", "cooler only", "hanya cooler",
    # Non-GPU marketplace noise
    "sepeda", "gunung", "road bike", "folding bike", "outdoor", "foster", "sumax", "polygon", "united",
    "gundam", "gunpla", "bandai", "mokit", "figure", "figurine", "model kit", "tamiya", "hotwheels", "lego",
    "kamar", "kost", "kontrakan", "sewa", "rumah", "apartemen", "tanah", "mobil", "motor", "helm",
    "baju", "sepatu", "celana", "jaket", "tas", "meja", "kursi", "lemari", "ps4", "ps5", "iphone",
    # PC rakitan / laptop (bukan VGA lepasan)
    "pc gaming", "cpu gaming", "komputer", "laptop", "notebook",
    "pc rakitan", "rakitan pc", "fullset pc", "pc fullset", "full set pc",
    "1 set pc", "satu set pc", "set pc", "all in one", "aio pc",
    "rig gaming", "mining rig", "gaming rig",
    "fullset ryzen", "fullset intel", "fullset core i",
    "fullset i3", "fullset i5", "fullset i7", "fullset i9",
    "paket pc", "pc render", "pc editing", "cpu rakitan",
]

# Keyword barang baru (reject karena fokus second/bekas)
BANNED_NEW_ITEMS = ["bnib", "brand new", "bnob", "baru garansi", "stok ready", "stok baru"]

# Frasa aman — override blacklist jika ditemukan (seller bilang "no minus" bukan berarti "minus")
SAFE_PHRASES = [
    "no minus", "tanpa minus", "non minus", "gak ada minus", "tidak ada minus",
    "no artefak", "tanpa artefak", "bebas artefak", "anti artefak",
    "bukan matot", "bukan kanibal", "bukan bahan", "bukan bekas servis", "tanpa kendala",
    "dijamin aman", "normal jaya", "siap pakai", "tes lancar", "lulus tes",
]

# ==============================================================================
# HARGA MINIMUM (Pancingan / DP / Aksesori)
# ==============================================================================
MIN_PRICE_FLOOR = 800_000

# ==============================================================================
# TIERING VENDOR — Sesuai gpu_scraper.md Section 2
# ==============================================================================

# Brand resmi Indonesia -> canonical name
BRAND_MAP = {
    "asus": "ASUS", "msi": "MSI", "gigabyte": "GIGABYTE", "zotac": "ZOTAC",
    "colorful": "COLORFUL", "palit": "PALIT", "galax": "GALAX", "inno3d": "INNO3D",
    "asrock": "ASROCK", "powercolor": "POWERCOLOR", "sapphire": "SAPPHIRE",
    "xfx": "XFX", "evga": "EVGA", "pny": "PNY", "gainward": "GAINWARD", "manli": "MANLI",
}

# Infer brand dari keyword produk (jika brand tidak disebut eksplisit)
BRAND_INFERENCE = {
    "rog": "ASUS", "strix": "ASUS", "tuf": "ASUS", "proart": "ASUS", "dual": "ASUS",
    "suprim": "MSI", "ventus": "MSI", "mech": "MSI",
    "aorus": "GIGABYTE", "eagle": "GIGABYTE", "windforce": "GIGABYTE", "vision": "GIGABYTE",
    "nitro": "SAPPHIRE", "pulse": "SAPPHIRE", "toxic": "SAPPHIRE",
    "red devil": "POWERCOLOR", "hellhound": "POWERCOLOR", "fighter": "POWERCOLOR",
    "igame": "COLORFUL", "vulcan": "COLORFUL",
    "hof": "GALAX",
    "amp holo": "ZOTAC", "twin edge": "ZOTAC", "trinity": "ZOTAC",
    "phantom": "GAINWARD",
    "gamerock": "PALIT",
}

# Cooler tiers (multiplier harga & score bonus)
COOLER_TIERS = {
    "S+": {
        "multiplier": 1.15,
        "score_bonus": 15,
        "keywords": [
            "rog matrix", "suprim x", "aorus xtreme", "kingpin",
            "hof", "toxic", "liquid devil", "kudan",
        ],
    },
    "S": {
        "multiplier": 1.10,
        "score_bonus": 10,
        "keywords": [
            "rog strix", "strix", "aorus master", "gaming z trio",
            "ftw3", "nitro+", "nitro plus", "nitro", "red devil",
            "amp extreme", "amp holo", "vulcan", "merc",
        ],
    },
    "A": {
        "multiplier": 1.0,
        "score_bonus": 0,
        "keywords": [
            "tuf", "proart", "gaming x", "gaming oc", "vision", "aero",
            "xc3", "pulse", "hellhound", "trinity", "gamerock",
            "qick", "taichi", "phantom gaming", "phantom",
            "igame advanced", "xlr8",
        ],
    },
    "B": {
        "multiplier": 0.90,
        "score_bonus": -10,
        "keywords": [
            "dual", "ventus", "mech", "eagle", "windforce",
            "twin edge", "fighter", "gamingpro", "gaming pro",
            "1-click oc", "1 click oc", "swft", "challenger",
            "battleax", "battle ax", "ultra", "twin x2",
            "verto", "gallardo",
            "single fan", "1 fan", "1fan", "itx", "mini",
            "aero itx", "phoenix", "stormx",
        ],
    },
}

from rapidfuzz import process, fuzz

# ==============================================================================
# STAGE 2: DESKRIPSI DEEP SCAN (RED FLAGS & GREEN FLAGS)
# ==============================================================================
STAGE2_RED_FLAGS = [
    "minus", "artefak", "artifact", "mati", "matot", "rusak", "servisan", 
    "pernah bongkar", "bekas mining", "kipas mati", "panas", "overheat", 
    "no display", "blank", "error", "kendala", "hanya dus", "box only",
    "tanpa unit", "hanya kipas"
]

STAGE2_GREEN_FLAGS = [
    "garansi resmi", "garansi on", "garansi aktif", "mulus", "fullset", 
    "like new", "segel", "belum pernah bongkar", "bukan bekas mining",
    "pribadi", "pemakaian pribadi"
]


def match_gpu_model(title: str) -> str | None:
    """Fuzzy matching untuk model GPU menggunakan RapidFuzz."""
    t_low = title.lower()
    
    # Prioritas 1: Exact substring match (lebih aman dari salah fuzzy)
    for model in FLIPPING_TARGETS_SORTED:
        if model in t_low:
            return model
            
    # Prioritas 2: Fuzzy Token Set Ratio (menangkap typo seperti "rtx3060", "rx 6600xt")
    match = process.extractOne(t_low, FLIPPING_TARGETS_SORTED, scorer=fuzz.token_set_ratio, score_cutoff=85)
    if match:
        return match[0]
        
    return None


def detect_brand(title: str) -> str:
    """Deteksi merk dengan Fuzzy Matching."""
    t_low = title.lower()
    BRANDS = ["ASUS", "MSI", "Gigabyte", "Zotac", "Galax", "Colorful", "Palit", "Sapphire", "PowerColor", "XFX", "ASRock", "PNY", "Inno3D", "Gainward", "Manli"]
    
    for brand in BRANDS:
        if brand.lower() in t_low:
            return brand
            
    match = process.extractOne(t_low, BRANDS, scorer=fuzz.partial_ratio, score_cutoff=80)
    if match:
        return match[0]
        
    return "OEM"


def get_cooler_tier(title: str) -> tuple[str, float, int]:
    """Cari kasta cooler dengan Fuzzy Matching untuk toleransi typo (misal 'strixx')."""
    t_low = title.lower()
    best_tier = "A"
    best_mult = 1.0
    best_bonus = 0
    
    # Ratakan semua keyword tier ke dalam dictionary untuk fuzzy search
    tier_map = {}
    for t_name, data in COOLER_TIERS.items():
        for kw in data["keywords"]:
            tier_map[kw] = (t_name, data["multiplier"], data["score_bonus"])
            
    # 1. Exact match dulu
    for kw, (t_name, mult, bonus) in tier_map.items():
        if kw in t_low:
            return t_name, mult, bonus
            
    # 2. Fuzzy match
    match = process.extractOne(t_low, list(tier_map.keys()), scorer=fuzz.partial_ratio, score_cutoff=85)
    if match:
        matched_kw = match[0]
        return tier_map[matched_kw]
        
    return best_tier, best_mult, best_bonus


def is_title_clean(title: str) -> bool:
    """
    Cek apakah judul bersih dari blacklist (non-GPU, brand sampah, barang baru).
    Return True jika lolos semua filter.
    """
    t = title.lower()

    # Bersihkan safe phrases dulu
    for safe in SAFE_PHRASES:
        t = t.replace(safe, "")

    if any(b in t for b in BANNED_NON_GPU):
        return False
    if any(b in t for b in BANNED_JUNK_BRANDS):
        return False
    if any(b in t for b in BANNED_NEW_ITEMS):
        return False
    if any(m in t for m in BANNED_JUNK_MODELS):
        return False
    return True


def parse_price(text: str) -> int:
    """Ekstrak angka harga dari string kotor (misal: 'Rp 4.500.000')."""
    import re
    numbers = re.sub(r"[^\d]", "", text)
    return int(numbers) if numbers else 0


def is_valid_search_result(title: str) -> bool:
    """
    Prefilter cepat untuk Scraper: 
    Harus lolos blacklist (is_title_clean) DAN wajib mengandung regex model GPU yang valid.
    """
    if not is_title_clean(title):
        return False
    if not GPU_SEARCH_REGEX.search(title.lower()):
        return False
    return True


# ==============================================================================
# SEARCH QUERIES — Broad queries yang mencakup semua varian (Ti, Super, XT)
# Sesuai spec: hanya RTX 2060+ dan RX 6600 XT+
# ==============================================================================
SEARCH_QUERIES = [
    "vga rtx 4060", "vga rtx 4070", "vga rtx 3060", "vga rtx 3070",
    "vga rtx 3050", "vga rtx 2060", "vga rtx 2070", "vga rtx 3080",
    "vga rx 6600 xt", "vga rx 6700", "vga rx 7600",
]

# Alert behavior
ALERT_UNPRICED = True
