# GPU SCRAPER & MARKET SNIPER SPECIFICATION (INDONESIAN MARKET)

## 🧠 CORE ARCHITECTURE & PHILOSOPHY
- **Pure Local Self-Learning:** 100% berjalan mandiri tanpa ketergantungan API LLM eksternal. Sistem belajar dinamis dari agregasi data nyata yang berhasil discrap.
- **Dua Tahap Scraping (Two-Stage Selective):**
  1. *Tahap 1 (Fast Search Stream):* Ambil judul, harga, link, foto, dan lokasi dari halaman pencarian utama.
  2. *Tahap 2 (Selective Detail Deep Scrape):* Hanya buka halaman detail iklan jika lolos saringan harga/model tahap 1. Ambil deskripsi lengkap untuk deteksi garansi, minus, dan kelengkapan kotak tanpa memicu rate-limit/ban.
- **Resource Ultra-Lightweight:** Blokir aset berat (`image`, `media`, `font`, `stylesheet`) via Playwright route interception. Hemat RAM 70% dan bebas lag.
- **Stabilitas Nonstop:** CMD QuickEdit dimatikan otomatis, watchdog loop auto-healing me-restart bot jika crash dan membasmi zombie Chromium.

---

## 1. KNOWLEDGE BASE: ARSITEKTUR GPU MINIMAL (STRICT RULES)
Listing di luar model di bawah ini **WAJIB DITOLAK** (`REJECTED_LOW_SPEC`):

### NVIDIA (Minimum RTX 2060)
- **Turing:** RTX 2060 (6GB/12GB), RTX 2060 Super, RTX 2070, RTX 2070 Super, RTX 2080, RTX 2080 Super, RTX 2080 Ti
- **Ampere:** RTX 3050, RTX 3060 (8GB/12GB), RTX 3060 Ti, RTX 3070, RTX 3070 Ti, RTX 3080, RTX 3080 Ti, RTX 3090, RTX 3090 Ti
- **Ada Lovelace:** RTX 4060, RTX 4060 Ti, RTX 4070, RTX 4070 Super, RTX 4070 Ti, RTX 4070 Ti Super, RTX 4080, RTX 4080 Super, RTX 4090
- *(GTX 16xx, GTX 10xx, GT series OTOMATIS DITOLAK).*

### AMD RADEON (Minimum RX 6600 XT)
- **RDNA 2:** RX 6600 XT, RX 6650 XT, RX 6700, RX 6700 XT, RX 6750 XT, RX 6800, RX 6800 XT, RX 6900 XT, RX 6950 XT
- **RDNA 3:** RX 7600, RX 7600 XT, RX 7700 XT, RX 7800 XT, RX 7900 GRE, RX 7900 XT, RX 7900 XTX
- *(RX 6600 non-XT, RX 6500 XT, RX 6400, RX 580/570/480/470 OTOMATIS DITOLAK).*

---

## 2. KNOWLEDGE BASE: VENDOR RESMI INDONESIA & TIERING
Hanya menerima vendor resmi bergaransi distributor Indonesia. Brand Eropa/non-lokal (cth: KFA2) tidak digunakan.

### Brand Whitelist & Tiering Nilai:
- **Tier S+ (Enthusiast Flagship) | Multiplier: +15% (Score Bonus +15)**
  *Varian:* ASUS ROG Matrix, MSI Suprim X, Gigabyte Aorus Xtreme, EVGA Kingpin, Galax HOF, Sapphire Toxic, PowerColor Liquid Devil, Colorful iGame KUDAN.
- **Tier S (Premium Flagship) | Multiplier: +10% (Score Bonus +10)**
  *Varian:* ASUS ROG Strix, Gigabyte Aorus Master, MSI Gaming Z Trio, EVGA FTW3, Sapphire Nitro+, PowerColor Red Devil, Zotac AMP Extreme, Colorful iGame Vulcan, XFX Speedster MERC.
- **Tier A (Mid-High Standard) | Multiplier: +0% (Baseline)**
  *Varian:* ASUS TUF, ASUS ProArt, MSI Gaming X, Gigabyte Gaming OC, Gigabyte Vision/Aero, EVGA XC3, Sapphire Pulse, PowerColor Hellhound, Zotac Trinity, Palit GameRock, XFX Speedster QICK, ASRock Taichi/Phantom Gaming, Colorful iGame Advanced, PNY XLR8, Gainward Phantom.
- **Tier B (Entry MSRP) | Multiplier: -10% (Score Penalty -10)**
  *Varian:* ASUS Dual, MSI Ventus (2X/3X), MSI Mech, Gigabyte Eagle/Windforce, Zotac Twin Edge, PowerColor Fighter, Palit GamingPro/Dual, Galax EX/1-Click OC, XFX Speedster SWFT, ASRock Challenger, Colorful Ultra/BattleAx, Inno3D Twin X2, PNY Verto, Manli Gallardo.

### Brand Blacklist (Daur Ulang Chip Mining / Rekondisi Cina):
**TOLAK MUTLAK (`REJECTED_BRAND`):**
Aisurix, Vurrion, Mllse, Peladn, Jieshuo, Afox, Bulldozer, Soyo, Szmz, 51Risc, Veinida, Arktek, VenomRX, Buldozer, Varro, Imperion, Inforce, Kllisre.

---

## 3. KNOWLEDGE BASE: ANTI-PC RAKITAN, LAPTOP, & HARGA PANCINGAN
- **Blacklist Unit Non-VGA Lepasan (`REJECTED_NON_GPU_RIG`):**
  Tolak judul yang mengandung kata kunci unit PC utuh/laptop:
  `pc gaming`, `cpu gaming`, `komputer`, `laptop`, `notebook`, `pc rakitan`, `rakitan pc`, `fullset pc`, `pc fullset`, `full set pc`, `1 set pc`, `satu set pc`, `set pc`, `all in one`, `aio pc`, `rig gaming`, `mining rig`, `gaming rig`, `fullset ryzen`, `fullset intel`, `fullset core i`, `fullset i3/i5/i7/i9`, `paket pc`, `pc render`, `pc editing`, `cpu rakitan`.
- **Lantai Harga Minimum (`REJECTED_TOO_CHEAP`):**
  Harga di bawah **Rp 800.000** ditolak mutlak (menghapus trik seller posting DP, cicilan, pancingan chat Rp 10.500, atau aksesori).

---

## 4. SISTEM SELF-LEARNING & DECISION MATRIX
Perhitungan harga wajar murni kalkulasi matematis berbasis data histori SQLite lokal (`seen_deals.db`) dan Supabase:

1. **Dynamic Market Baseline:**
   - Hitung `median_price` menggunakan Interquartile Range (IQR) untuk membuang harga outlier ekstrem.
2. **Kasta Cooler & Tier:**
   - Triple Fan / Premium: `multiplier = 1.15`
   - Dual Fan: `multiplier = 1.00`
   - Single Fan / ITX: `multiplier = 0.88`
   - `adjusted_fair_value = median_price * tier_multiplier`
3. **Decision Matrix Flipper:**
   - **SNIPE:** Harga <= (`adjusted_fair_value` - 18%) -> Kirim alert Discord & tandai Steal Deal di Web.
   - **NEGO:** Harga antara (`adjusted_fair_value` - 17%) s/d (`adjusted_fair_value` - 5%) -> Simpan untuk dipantau/ditawar.
   - **SKIP:** Harga > (`adjusted_fair_value` - 5%) -> Abaikan (tidak ada margin cuan).

---

## 5. BEST PRACTICE VERIFIKASI GAMBAR: PERCEPTUAL HASHING (pHash)
- **Tolak Model Computer Vision / YOLO Lokal:**
  Pelatihan deteksi kipas lokal rapuh terhadap sudut miring, resolusi rendah, dan foto gelap di Facebook Marketplace.
- **Implementasi Perceptual Hash (64-bit pHash):**
  - Hitung pHash dari gambar listing.
  - **Deteksi Foto Sindikat:** Jika pHash cocok dengan postingan yang sudah ada tapi akun penjual/lokasi berbeda -> `REJECTED_DUPLICATE_SCAM`.
  - **Deteksi Gambar Brosur:** Deteksi kemiripan ekstrem dengan database gambar katalog pabrik (bukan foto unit riil di meja).

---

## 6. FORMAT DATA STANDARDISASI (INTERNAL & SYNC)
```json
{
  "title": "string",
  "normalized_chip": "string (cth: RTX 3060 TI)",
  "vendor": "string (cth: ASUS)",
  "variant": "string (cth: TUF GAMING OC)",
  "fan_type": "Triple Fan | Dual Fan | Single Fan",
  "tier": "S+ | S | A | B",
  "price": 0,
  "calculated_median_market": 0,
  "adjusted_fair_value": 0,
  "potential_margin": 0,
  "action_decision": "SNIPE | NEGO | SKIP | REJECTED_*",
  "platform": "Tokopedia | Facebook | Toco",
  "location": "string",
  "url": "string",
  "image_url": "string",
  "image_phash": "string",
  "is_steal_deal": true
}
```