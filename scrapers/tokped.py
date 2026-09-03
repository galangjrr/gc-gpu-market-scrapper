import os
import urllib.parse
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import parse_price, is_valid_search_result

async def scrape_tokopedia_vga(
    page,
    query: str = "vga rtx 3060",
    min_price: int = 1000000,
    max_price: int = 6000000,
    max_items: int = 30
):
    encoded_query = urllib.parse.quote(query)
    url = (
        f"https://www.tokopedia.com/search?"
        f"q={encoded_query}&condition=2&ob=9&pmin={min_price}&pmax={max_price}"
    )
    print(f"[*] Scraping Tokopedia (Second & Terbaru): {url}")
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        
        for _ in range(3):
            await page.mouse.wheel(0, 1500)
            await page.wait_for_timeout(1200)
            
        cards = await page.locator('div[data-ssr="contentProductsSRPSSR"] a, a[data-testid="lnkProductItem"]').all()
        print(f"[*] Menemukan {len(cards)} elemen produk Tokopedia")
        
        results = []
        seen_urls = set()
        
        for card in cards:
            href = await card.get_attribute("href")
            if not href or "/promo/" in href:
                continue
                
            clean_url = href.split("?")[0]
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
            
            raw_text = await card.inner_text()
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            
            title = ""
            price_str = ""
            location = ""
            
            for line in lines:
                if not title and len(line) > 5 and not line.startswith("Rp"):
                    title = line
                elif "rp" in line.lower() and not price_str:
                    price_str = line
                elif any(city in line.lower() for city in ["jakarta", "tangerang", "bekasi", "bogor", "depok", "bandung", "surabaya", "kab.", "kota"]):
                    location = line
                    
            if not title:
                continue

            if not is_valid_search_result(title):
                continue
                
            price_num = parse_price(price_str)
            if not (min_price <= price_num <= max_price):
                continue

            img_url = ""
            try:
                img_el = card.locator("img").first
                if await img_el.count() > 0:
                    img_url = await img_el.get_attribute("src") or await img_el.get_attribute("data-src") or ""
            except Exception:
                pass
                
            results.append({
                "title": title,
                "price_raw": price_str,
                "price": price_num,
                "location": location or "Indonesia",
                "condition": "Bekas",
                "image_url": img_url,
                "url": clean_url,
                "source": "tokopedia"
            })
                
            if len(results) >= max_items:
                break
                
        results.sort(key=lambda x: x["price"])
        print(f"[+] Berhasil scrape {len(results)} VGA second di Tokopedia")
        return results
        
    except Exception as e:
        print(f"[-] Error Tokopedia: {e}")
        return []
