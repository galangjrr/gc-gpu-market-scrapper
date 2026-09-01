import asyncio
import json
import re
from playwright.async_api import async_playwright

def parse_price(text: str) -> int:
    numbers = re.sub(r"[^\d]", "", text)
    return int(numbers) if numbers else 0

async def scrape_toco_vga(
    query: str = "vga rtx",
    min_price: int = 500000,
    max_price: int = 6000000,
    max_items: int = 25
):
    encoded_query = query.replace(" ", "%20")
    url = f"https://toco.id/search?q={encoded_query}"
    print(f"[*] Scraping Toco.id: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 900}
        )
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)
            
            # Scroll lazy load
            for _ in range(3):
                await page.mouse.wheel(0, 1500)
                await page.wait_for_timeout(800)
                
            # Ambil semua card listing di Toco
            cards = await page.locator('a[href*="/listing/"]').all()
            print(f"[*] Menemukan {len(cards)} item listing di Toco")
            
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
                        
                price_num = parse_price(price_str)
                norm_title = re.sub(r'[^a-zA-Z0-9]', '', title.lower()[:30])
                if norm_title in seen_titles:
                    continue
                seen_titles.add(norm_title)
                
                if min_price <= price_num <= max_price and title:
                    results.append({
                        "title": title,
                        "price_raw": price_str,
                        "price": price_num,
                        "location": location,
                        "condition": "Bekas/C2C",
                        "url": clean_url,
                        "source": "toco"
                    })
                    
                if len(results) >= max_items:
                    break
                    
            output_file = "toco_vga_deals.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            print(f"[+] Berhasil simpan {len(results)} VGA dari Toco ke {output_file}")
            return results
            
        except Exception as e:
            print(f"[-] Error Toco: {e}")
            return []
        finally:
            await browser.close()

if __name__ == "__main__":
    deals = asyncio.run(scrape_toco_vga("vga rtx", min_price=500000, max_price=6000000))
    print("\n--- HASIL SCRAPING TOCO ---")
    for d in deals[:5]:
        print(f"[{d['price_raw']}] {d['title']} | {d['location']}")
        print(f"   URL: {d['url']}")
