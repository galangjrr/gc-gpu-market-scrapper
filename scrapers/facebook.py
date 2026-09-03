import os
import re
import urllib.parse
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import parse_price, is_valid_search_result

def clean_card_lines(lines: list[str]) -> dict | None:
    filtered = [l for l in lines if l.lower() not in ["just listed", "baru terdaftar", "ships to you"]]
    if not filtered:
        return None
        
    price_indices = [
        i for i, line in enumerate(filtered)
        if re.search(r"(?:rp|idr|\$|free|gratis)", line, re.IGNORECASE)
    ]
    
    if price_indices:
        price_index = price_indices[-1]
        price_str = filtered[price_index]
    else:
        price_index = 0
        price_str = filtered[0]
        
    title = filtered[price_index + 1] if price_index + 1 < len(filtered) else ""
    location = filtered[price_index + 2] if price_index + 2 < len(filtered) else "-"
    
    if not title or not is_valid_search_result(title):
        return None
        
    price_num = parse_price(price_str)
    
    # Normalisasi harga ribuan (biasanya penjual tulis Rp 3.500 padahal maksudnya Rp 3.500.000)
    if 1000 <= price_num <= 9999:
        price_num *= 1000
    elif 10 <= price_num <= 999:
        price_num *= 10000
        
    return {
        "title": title,
        "price_raw": price_str,
        "price": price_num,
        "location": location or "-"
    }

async def scrape_fb_marketplace(
    page,
    query: str = "vga rtx",
    city: str = "jakarta",
    min_price: int = 1000000,
    max_price: int = 7000000,
    days_since_listed: int = 7,
    max_items: int = 30
):
    encoded_q = urllib.parse.quote(query)
    url = f"https://www.facebook.com/marketplace/{city}/search/?query={encoded_q}&daysSinceListed={days_since_listed}&sortBy=creation_time_descend"
    print(f"[*] Scraping FB Marketplace: {url}")
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        
        try:
            close_btn = page.locator('div[aria-label="Tutup"], div[aria-label="Close"]').first
            if await close_btn.is_visible(timeout=2000):
                await close_btn.click()
        except Exception:
            pass
        
        for _ in range(4):
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(1200)
            
        links = await page.locator('a[href*="/marketplace/item/"], a[href*="/commerce/listing/"]').all()
        print(f"[*] Menemukan {len(links)} link kartu produk FB")
        
        results = []
        seen_urls = set()
        
        for link in links:
            href = await link.get_attribute("href")
            if not href:
                continue
                
            clean_url = f"https://www.facebook.com{href.split('?')[0]}"
            
            if "/category/" in clean_url or "/search/" in clean_url:
                continue
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
            
            raw_text = await link.inner_text()
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            parsed = clean_card_lines(lines)
            if not parsed:
                continue
                
            if min_price <= parsed["price"] <= max_price:
                img_url = ""
                try:
                    img_el = link.locator("img").first
                    if await img_el.count() > 0:
                        img_url = await img_el.get_attribute("src") or ""
                except Exception:
                    pass
                parsed["image_url"] = img_url
                parsed["url"] = clean_url
                parsed["source"] = "facebook_marketplace"
                results.append(parsed)
                
            if len(results) >= max_items:
                break
                
        results.sort(key=lambda x: x["price"])
        print(f"[+] Berhasil filter {len(results)} VGA FB asli")
        return results
        
    except Exception as e:
        print(f"[-] Error FB: {e}")
        return []
