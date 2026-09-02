import json
import os
import statistics
import sqlite3
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Model yang dianalisis pasar
TARGET_MODELS = [
    "rtx 4060", "rtx 3070", "rtx 3060 ti", "rtx 3060", "rtx 3050",
    "rtx 2060 super", "rtx 2060", "gtx 1660 super", "gtx 1660 ti",
    "rx 7600", "rx 6700 xt", "rx 6600 xt", "rx 6600"
]

def calculate_market_prices():
    # Ambil data harga dari semua file scraping
    files = [os.path.join(BASE_DIR, f) for f in ["tokped_vga_deals.json", "fb_vga_deals.json", "toco_vga_deals.json"]]
    all_items = []
    
    for f_name in files:
        try:
            with open(f_name, "r", encoding="utf-8") as f:
                all_items.extend(json.load(f))
        except Exception:
            pass
            
    market_summary = {}
    
    for model in TARGET_MODELS:
        prices = []
        for item in all_items:
            title = item.get("title", "").lower()
            price = item.get("price", 0)
            
            # Cocokkan model & filter harga masuk akal (buang harga 0 / receh)
            if model in title and price >= 1000000:
                prices.append(price)
                
        if len(prices) >= 2:
            median_price = int(statistics.median(prices))
            avg_price = int(statistics.mean(prices))
            min_price = min(prices)
            max_price = max(prices)
            
            # Target kulak untung = 15% - 20% di bawah median pasar
            target_snipe = int(median_price * 0.84)
            estimasi_cuan = int(median_price * 0.16)
            
            market_summary[model.upper()] = {
                "sample_count": len(prices),
                "harga_pasar_median": f"Rp {median_price:,}",
                "harga_terendah": f"Rp {min_price:,}",
                "harga_tertinggi": f"Rp {max_price:,}",
                "target_kulak_snipe": f"Rp {target_snipe:,}",
                "estimasi_cuan": f"Rp {estimasi_cuan:,}"
            }
            
    with open(os.path.join(BASE_DIR, "market_prices.json"), "w", encoding="utf-8") as f:
        json.dump(market_summary, f, indent=2)
        
    return market_summary

if __name__ == "__main__":
    summary = calculate_market_prices()
    print("="*65)
    print("ESTIMASI HARGA PASAR SECOND & TARGET KULAK CUAN:")
    print("="*65)
    for model, data in summary.items():
        print(f"[{model}] (Sampel: {data['sample_count']} unit)")
        print(f"   - Harga Pasar Normal : {data['harga_pasar_median']}")
        print(f"   - Target Kulak Snipe : <= {data['target_kulak_snipe']}")
        print(f"   - Potensi Margin     : ~{data['estimasi_cuan']}")
        print("-" * 65)
