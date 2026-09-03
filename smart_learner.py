"""
smart_learner.py — Self-Learning Statistical Engine untuk VGA Hunter.
Menggunakan SQLite price_history untuk rolling IQR median.
Semua constants diambil dari config.py.
"""
import os
import re
import sqlite3

from config import DB_PATH, MIN_PRICE_FLOOR, FLIPPING_TARGETS, detect_brand


class SmartLearner:
    """
    Self-Learning Statistical Engine:
    - Anti-Poisoning: Menolak sampel harga troll/matot yang jauh dari baseline.
    - Rolling IQR Median: Hitung harga riil pasar (auto-prune >60 hari).
    - Dynamic Profit Margin: Margin mengecil untuk GPU Sultan (10jt+), membesar untuk entry-level.
    - Semantic Scoring: Kombinasi diskon matematis & keyword BU/Garansi.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Tabel riwayat harga historis
        c.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                price INTEGER NOT NULL,
                platform TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            c.execute("ALTER TABLE price_history ADD COLUMN brand TEXT DEFAULT 'unknown'")
        except sqlite3.OperationalError:
            pass

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_lookup
            ON price_history(model, brand, created_at)
        """)

        # Auto-Prune data > 60 hari
        try:
            c.execute("DELETE FROM price_history WHERE created_at < datetime('now', '-60 days')")
        except Exception:
            pass

        conn.commit()
        conn.close()

    def record_deal_sample(self, model: str, price: int, platform: str, title: str, is_steal: bool):
        """Catat data sampel baru ke memori dengan Anti-Poisoning."""
        model_key = model.lower()
        if price < MIN_PRICE_FLOOR or price > 30_000_000 or not model_key:
            return

        # 1. Anti-Poisoning: Tolak harga troll/ngawur agar median pasar tidak rusak
        baseline_min, baseline_max = FLIPPING_TARGETS.get(model_key, (0, 0))
        if baseline_max > 0:
            if price > baseline_max * 1.8:  # 80% lebih mahal dari target = Listing Overprice (Abaikan)
                return
            if price < baseline_min * 0.6:  # 40% di bawah harga lantai = Curiga Matot/Scam (Abaikan)
                return

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        brand = detect_brand(title).lower()

        c.execute(
            "INSERT INTO price_history (model, price, platform, brand) VALUES (?, ?, ?, ?)",
            (model_key, price, platform, brand),
        )

        conn.commit()
        conn.close()

    def get_learned_market_stats(self, model: str, title: str = "") -> dict | None:
        """
        Hitung statistik pasar dinamis menggunakan IQR & Dynamic Margin.
        """
        brand = detect_brand(title).lower()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        prices = []
        if brand != "oem":
            c.execute("""
                SELECT price FROM price_history
                WHERE model = ? AND brand = ? AND created_at >= datetime('now', '-30 days')
                ORDER BY price ASC
            """, (model.lower(), brand))
            prices = [row[0] for row in c.fetchall()]

        # Fallback ke model-generik jika sampel brand < 3
        if len(prices) < 3:
            c.execute("""
                SELECT price FROM price_history
                WHERE model = ? AND created_at >= datetime('now', '-30 days')
                ORDER BY price ASC
            """, (model.lower(),))
            prices = [row[0] for row in c.fetchall()]

        conn.close()

        if len(prices) < 3:
            return None

        # 2. IQR filtering: buang outlier ekstrem yang lolos filter awal
        n = len(prices)
        q1 = prices[n // 4]
        q3 = prices[(3 * n) // 4]
        iqr = q3 - q1
        lower_bound = q1 - int(1.5 * iqr)
        upper_bound = q3 + int(1.5 * iqr)

        clean_prices = [p for p in prices if lower_bound <= p <= upper_bound]
        if not clean_prices:
            clean_prices = prices  # Fallback

        cn = len(clean_prices)
        median = clean_prices[cn // 2] if cn % 2 != 0 else int((clean_prices[cn // 2 - 1] + clean_prices[cn // 2]) / 2)

        # 3. Dynamic Profit Margin (Semakin mahal GPU, persentase cuan bisa ditekan agar kompetitif)
        if median <= 2_500_000:
            margin_pct = 0.80  # Target Profit 20% (GPU Murah, wajib cuan gede persenan)
        elif median <= 5_000_000:
            margin_pct = 0.85  # Target Profit 15%
        elif median <= 10_000_000:
            margin_pct = 0.88  # Target Profit 12%
        else:
            margin_pct = 0.90  # Target Profit 10% (GPU 10jt+, untung sejuta udah bungkus)

        smart_max_kulak = int(median * margin_pct)
        smart_min_floor = int(median * 0.55)

        return {
            "samples": len(prices),
            "dynamic_median": median,
            "smart_max_kulak": smart_max_kulak,
            "smart_min_floor": smart_min_floor,
        }

    def compute_steal_score(self, title: str, price: int, model: str, base_max_kulak: int) -> int:
        """
        Skor kelayakan deal berdasarkan diskon matematis + semantic keyword.
        """
        if base_max_kulak <= 0:
            return 0

        discount_pct = 1.0 - (price / base_max_kulak)
        
        # Asumsi 15% di bawah batas kulak = 100 skor
        math_score = int((discount_pct / 0.15) * 100)
        
        # 4. Semantic Keyword Scoring
        word_bonus = 0
        t_low = title.lower()
        if any(w in t_low for w in ["bu", "butuh uang", "urgent", "pribadi"]):
            word_bonus += 15
        if any(w in t_low for w in ["garansi resmi", "garansi on", "garansi aktif"]):
            word_bonus += 10
        if any(w in t_low for w in ["mulus", "fullset", "like new"]):
            word_bonus += 5

        final_score = math_score + word_bonus
        return min(100, max(0, final_score))


learner = SmartLearner()
