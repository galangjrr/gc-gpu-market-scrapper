import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

def parse_price(text: str) -> int:
    numbers = re.sub(r"[^\d]", "", text)
    return int(numbers) if numbers else 0

async def scrape_tokopedia_vga(
    query: str = "vga rtx 3060",
    min_price: int = 1000000,
    max_price: int = 6000000,
    max_items: int = 30
):
    encoded_query = query.replace(" ", "%20")
    url = (
        f"https://www.tokopedia.com/search?"
        f"q={encoded_query}&condition=2&ob=9&pmin={min_price}&pmax={max_price}"
    )
    print(f"[*] Scraping Tokopedia (Second & Terbaru): {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="id-ID",
            extra_http_headers={
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1"
            }
        )
        
        page = await context.new_page()
        await page.route("**/*.{png,jpg,jpeg,webp,svg,gif,woff,woff2,css}", lambda route: route.abort())
        
        try:
            # Tokopedia butuh wait networkidle atau load
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)
            
            # Scroll pelan-pelan
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
                        
                price_num = parse_price(price_str)
                
                # Ekstraksi Foto Thumbnail Produk
                img_url = ""
                try:
                    img_el = card.locator("img").first
                    if await img_el.count() > 0:
                        img_url = await img_el.get_attribute("src") or await img_el.get_attribute("data-src") or ""
                except Exception:
                    pass
                    
                if min_price <= price_num <= max_price and title:
                    t_low = title.lower()
                    if any(k in t_low for k in ["bnib", "brand new", "bnob", "baru garansi", "stok ready", "stok baru"]):
                        continue
                    
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
            
            output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokped_vga_deals.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            print(f"[+] Berhasil simpan {len(results)} VGA second ke {output_file}")
            return results
            
        except Exception as e:
            print(f"[-] Error Tokopedia: {e}")
            return []
        finally:
            await browser.close()

if __name__ == "__main__":
    deals = asyncio.run(scrape_tokopedia_vga("vga rtx 3060", min_price=2000000, max_price=5500000))
    print(f"Total hasil: {len(deals)}")
