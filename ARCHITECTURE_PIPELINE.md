# DOKUMEN ARSITEKTUR: VGA HUNTER PIPELINE (PATEN SISTEM)

Dokumen ini adalah acuan baku (*Single Source of Truth*) perancangan sistem pipeline scraping dan pemurnian data VGA second.

---

## 1. ALUR DATA TIGA TAHAP (DATA REFINERY PIPELINE)

```
[Web/App Scraper] -> (Raw Ingest) -> [Tabel Raw Bronze]
                                             |
                                     (Learner / Refiner)
                                             |
                +----------------------------+---------------------------+
                |                                                        |
       [Tahap 1: Fast Regex Engine]                             [Tahap 2: Micro Multimodal API]
       - Ekstrak Model & Varian                                 - Deep text nuance (BU, minus terselubung)
       - Ekstrak Harga Asli (Anti-DP/Cicil)                     - Visual inspection (karat bracket, korosi)
       - Spotting Segel (Baut/Repaste)                          - Dilakukan HANYA pd kandidat potensial
                |                                                        |
                +----------------------------+---------------------------+
                                             |
                                     [Tabel Gold Silver]
                                             |
                                     (Dashboard & Web)
                           - Data bersih bebas bias statistik
                           - Keputusan akhir di tangan manusia
```

---

## 2. KOMPONEN UTAMA

### A. Bot Scraper (Raw Ingestion)
- **Tugas:** Menangkap listing mentah dari Tokopedia, Facebook Marketplace, dan Toco.id.
- **Prinsip:** Tidak melakukan filter harga kaku di level browser. Simpan apa adanya (judul, harga asli, URL, nama seller, deskripsi, foto).
- **Mode Eksekusi:** 
  - Booting selalu dalam mode **`STANDBY`**.
  - Menunggu trigger perintah (`SCAN_NOW`) dan parameter pencarian dari Web UI sebelum membuka browser.

### B. Bot Refiner / Learner (Data Cleaning & Intelligence)
- **Sub-sistem 1: Regex Extraction Engine (85% Beban Kerja)**
  - Menguraikan judul & deskripsi: Chipset, Merk, Seri/Kasta Cooler, VRAM.
  - Normalisasi harga: Mengidentifikasi harga palsu (Rp 1.000, DP Rp 500.000, sistem cicilan) dan mengabaikannya.
  - Tagging segel & riwayat: Deteksi kata kunci `ganti pasta`, `bongkar`, `segel utuh`, `pemakaian pribadi`.
- **Sub-sistem 2: Micro Multimodal Vision (15% Kandidat Potensial)**
  - Dipanggil khusus untuk listing yang masuk zona harga wajar / murah.
  - Mengirim URL gambar ke Gemini Flash Vision untuk memverifikasi:
    1. Ada karat / korosi pada bracket I/O atau heatsink?
    2. Kesesuaian fisik unit dengan tipe pada judul.

### C. Basis Data (Supabase Postgres)
- **Tabel `raw_scrapes`:** Menampung hasil dump mentah tanpa validasi ketat.
- **Tabel `gold_deals`:** Menampung data yang sudah diurai, terstruktur, dan memiliki status kelayakan jelas (`APPROVED`, `WARNING_FLAW`, `REJECTED_LOW_SPEC`).
- **Tabel `bot_commands`:** Pusat kendali state (`STANDBY`, `SCANNING`, `PAUSED`) serta penyimpanan parameter dinamis (`queries`, `platforms`, `spotter_config`).

### D. Kontrol & Keputusan Manusia (Web UI)
- **Menghapus Bias Formula:** Tidak menggunakan angka median otomatis untuk menentukan "pasti untung".
- **Parameter Transparan:** User menentukan batas kulak target dan kata kunci spotter langsung dari browser HP/PC.
- **Katalog Bersih:** Web hanya menampilkan data dari tabel `gold_deals`.

---

## 3. ATURAN TOLAK MUTLAK (REJECT RULES)
1. **Low Spec:** Di bawah RTX 2060 (NVIDIA) atau di bawah RX 6600 XT (AMD) -> Langsung buang ke status `REJECTED_LOW_SPEC`.
2. **Non-GPU:** Rakitan PC full set, laptop, casing, heatsink only, dus kosong.
3. **Chip Rekondisi:** Brand rekondisi pabrik Cina non-resmi (Aisurix, Peladn, Mllse, dsb).
