import os
import re
import urllib.parse
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import parse_price, is_valid_search_result

async def scrape_toco_vga(
    page,
    query: str = "vga rtx",
    min_price: int = 800000,
    max_price: int = 6000000,
    max_items: int = 25
):
    encoded_query = urllib.parse.quote(query)
    url = f"https://toco.id/search?q={encoded_query}"
    print(f"[*] Scraping Toco.id: {url}")
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2500)
        
        for _ in range(3):
            await page.mouse.wheel(0, 1500)
            await page.wait_for_timeout(800)
            
        cards = await page.locator('a[href*="/listing/"]').all()
        print(f"[*] Menemukan {len(cards)} item listing mentah di Toco")
        
        results = []
        seen_urls = set()
        seen_titles = set()
        
        for card in cards:
            href = await card.get_attribute("href")
            if not href:
                continue
                
            clean_url = f"https://toco.id{href}" if href.startswith("/") else href
            clean_url = clean_url.split("?")[0]
            
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
            
            raw_text = await card.inner_text()
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            if not lines:
                continue
                
            filtered = [l for l in lines if not l.lower().startswith("sisa") and not l.lower().startswith("terjual") and not l.isdigit()]
            
            title = ""
            price_str = ""
            location = "Indonesia"
            
            for line in filtered:
                if "rp" in line.lower() and not price_str:
                    price_str = line
                elif any(c in line.lower() for c in ["kota", "kabupaten", "kab."]):
                    location = line
                elif not title and len(line) > 3:
                    title = line
                    
            if not title or not is_valid_search_result(title):
                continue
                
            price_num = parse_price(price_str)
            if not (min_price <= price_num <= max_price):
                continue

            norm_title = re.sub(r'[^a-zA-Z0-9]', '', title.lower()[:30])
            if norm_title in seen_titles:
                continue
            seen_titles.add(norm_title)
            
            img_url = ""
            try:
                img_el = card.locator("img").first
                if await img_el.count() > 0:
                    img_url = await img_el.get_attribute("src") or ""
            except Exception:
                pass
                
            results.append({
                "title": title,
                "price_raw": price_str,
                "price": price_num,
                "location": location,
                "condition": "Bekas/C2C",
                "image_url": img_url,
                "url": clean_url,
                "source": "toco"
            })
                
            if len(results) >= max_items:
                break
                
        print(f"[+] Berhasil filter {len(results)} VGA Toco asli")
        return results
        
    except Exception as e:
        print(f"[-] Error Toco: {e}")
        return []
