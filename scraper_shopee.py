import asyncio
import json
import re
import os
from playwright.async_api import async_playwright

def parse_price(text: str) -> int:
    numbers = re.sub(r"[^\d]", "", text)
    return int(numbers) if numbers else 0

async def scrape_shopee_vga(
    query: str = "vga rtx 3060",
    min_price: int = 1000000,
    max_price: int = 6000000,
    max_items: int = 20
):
    # Simpan session login/cookie di folder lokal
    user_data_dir = os.path.abspath("./shopee_session")
    encoded_query = query.replace(" ", "%20")
    url = f"https://shopee.co.id/search?keyword={encoded_query}&sortBy=ctime"
    print(f"[*] Scraping Shopee via Persistent Session: {url}")
    
    async with async_playwright() as p:
        # Gunakan context persisten agar cookie & bypass captcha tersimpan
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3500)
            
            # Scroll ambil item
            for _ in range(3):
                await page.mouse.wheel(0, 1500)
                await page.wait_for_timeout(1200)
                
            items = await page.locator('a[data-sqe="link"], a[href*="-i."]').all()
            print(f"[*] Menemukan {len(items)} item Shopee")
            
            results = []
            seen_urls = set()
            
            for item in items:
                href = await item.get_attribute("href")
                if not href:
                    continue
                    
                clean_url = f"https://shopee.co.id{href.split('?')[0]}" if href.startswith("/") else href.split("?")[0]
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)
                
                raw_text = await item.inner_text()
                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
                
                title = ""
                price_str = ""
                location = ""
                
                for line in lines:
                    if not title and len(line) > 6 and not "rp" in line.lower() and not "%" in line:
                        title = line
                    elif "rp" in line.lower() and not price_str:
                        price_str = line
                    elif any(c in line.lower() for c in ["kota", "kab.", "jakarta", "tangerang", "bekasi", "bogor", "depok"]):
                        location = line
                        
                price_num = parse_price(price_str)
                if min_price <= price_num <= max_price and title:
                    results.append({
                        "title": title,
                        "price_raw": price_str,
                        "price": price_num,
                        "location": location or "Indonesia",
                        "condition": "Bekas/Umum",
                        "url": clean_url,
                        "source": "shopee"
                    })
                    
                if len(results) >= max_items:
                    break
                    
            output_file = "shopee_vga_deals.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            print(f"[+] Berhasil simpan {len(results)} VGA dari Shopee ke {output_file}")
            return results
            
        except Exception as e:
            print(f"[-] Error Shopee: {e}")
            return []
        finally:
            await context.close()

if __name__ == "__main__":
    deals = asyncio.run(scrape_shopee_vga("vga rtx 3060", min_price=1500000, max_price=5500000))
    for d in deals[:5]:
        print(f"[{d['price_raw']}] {d['title']} | {d['url']}")
