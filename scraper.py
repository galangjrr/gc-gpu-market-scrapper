import asyncio
import json
import re
import urllib.parse
from playwright.async_api import async_playwright

# REGEX PRESISI UNTUK GPU SAJA (TIDAK AKAN COCOK DENGAN GUNDAM RX-78 ATAU MAINAN)
GPU_REGEX_PATTERN = re.compile(
    r"\b(?:"
    r"rtx\s*\d{4}(?:\s*ti|\s*super)?"
    r"|gtx\s*\d{3,4}(?:\s*ti|\s*super)?"
    r"|rx\s*(?:7900\s*xtx|7900\s*xt|7800\s*xt|7700\s*xt|7600\s*xt|7600|6950\s*xt|6900\s*xt|6800\s*xt|6800|6750\s*xt|6700\s*xt|6650\s*xt|6600\s*xt|6600|6500\s*xt|5700\s*xt|5700|5600\s*xt|5500\s*xt|590|580|570)"
    r"|arc\s*[ab]\d{3}"
    r"|radeon\s*rx"
    r"|geforce\s*(?:rtx|gtx)"
    r")\b",
    re.IGNORECASE
)

# BLACKLIST MUTLAK NON-GPU & VGA RUSAK / NO DISPLAY / MATOT / SAMPAH
BANNED_NON_GPU = [
    "no display", "nodisplay", "no disp", "no dp", "matot", "mati total", "mati",
    "artefak", "artifact", "artifak", "garis", "bangkai", "kanibal", "kanibalan",
    "part saja", "part only", "rusak", "servisan", "short", "hangus", "gosong",
    "hanya dus", "box saja", "kotak saja", "dus saja", "cooler only", "heatsink",
    "fan replacement", "kipas saja", "backplate", "bracket", "kabel riser", "riser card",
    "kabel pcie", "dock egpu", "casing egpu", "dummy plug", "converter", "thermal pad",
    "baut", "gt 710", "gt 730", "gt 610", "gt 210", "sepeda", "gunung", "road bike",
    "gundam", "gunpla", "bandai", "mokit", "figure", "figurine", "model kit", "tamiya",
    "kamar", "kost", "kontrakan", "sewa", "rumah", "apartemen", "tanah", "mobil", "motor"
]

def parse_price(text: str) -> int:
    numbers = re.sub(r"[^\d]", "", text)
    return int(numbers) if numbers else 0

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
    
    if not title:
        return None
        
    t_low = title.lower()
    
    # 1. Reject non-GPU & mainan/gundam
    if any(b in t_low for b in BANNED_NON_GPU):
        return None
        
    # 2. Wajib lolos Regex GPU ketat
    if not GPU_REGEX_PATTERN.search(t_low):
        return None
        
    price_num = parse_price(price_str)
    
    # Normalisasi harga ribuan
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
    query: str = "vga rtx 3060",
    city: str = "jakarta",
    min_price: int = 1000000,
    max_price: int = 7000000,
    days_since_listed: int = 7,
    max_items: int = 30
):
    encoded_q = urllib.parse.quote(query)
    url = f"https://www.facebook.com/marketplace/{city}/search/?query={encoded_q}&daysSinceListed={days_since_listed}&sortBy=creation_time_descend"
    print(f"[*] Scraping FB Marketplace: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="id-ID"
        )
        
        page = await context.new_page()
        await page.route("**/*.{png,jpg,jpeg,webp,svg,gif,woff,woff2}", lambda route: route.abort())
        
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
                    parsed["url"] = clean_url
                    parsed["source"] = "facebook_marketplace"
                    results.append(parsed)
                    
                if len(results) >= max_items:
                    break
                    
            results.sort(key=lambda x: x["price"])
            
            output_file = "fb_vga_deals.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            print(f"[+] Berhasil filter {len(results)} VGA FB asli ke {output_file}")
            return results
            
        except Exception as e:
            print(f"[-] Error FB: {e}")
            return []
        finally:
            await browser.close()

if __name__ == "__main__":
    deals = asyncio.run(scrape_fb_marketplace("vga rtx 3060", city="jakarta", min_price=1000000, max_price=7000000))
    print(f"Total VGA FB Valid: {len(deals)}")
    for item in deals[:5]:
        print(f"[{item['price_raw']}] {item['title']} | {item['location']}")
        print(f"   URL: {item['url']}")
