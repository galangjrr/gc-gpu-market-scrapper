import asyncio
import json
import re
import urllib.parse
from playwright.async_api import async_playwright

# REGEX MUTLAK: HANYA MODEL GPU NYATA (NVIDIA / AMD / INTEL)
GPU_STRICT_REGEX = re.compile(
    r"\b(?:"
    r"rtx\s*(?:4090|4080|4070|4060|3090|3080|3070|3060|3050|2080|2070|2060)(?:\s*(?:ti|super))?"
    r"|gtx\s*(?:1660|1650|1080|1070|1060|1050)(?:\s*(?:ti|super))?"
    r"|rx\s*(?:7900|7800|7700|7600|6950|6900|6800|6750|6700|6650|6600|6500|5700|5600|5500|590|580|570)(?:\s*xtx|\s*xt)?"
    r"|arc\s*(?:a770|a750|a580|b580|b570)"
    r")\b",
    re.IGNORECASE
)

# BLACKLIST MUTLAK NON-GPU (SEPEDA, GUNDAM, PROPERTI, BAJU, DLL)
BANNED_NON_GPU = [
    "sepeda", "gunung", "road bike", "folding bike", "outdoor", "foster", "sumax", "polygon", "united",
    "gundam", "gunpla", "bandai", "mokit", "figure", "figurine", "model kit", "tamiya", "hotwheels", "lego",
    "kamar", "kost", "kontrakan", "sewa", "rumah", "apartemen", "tanah", "mobil", "motor", "helm",
    "baju", "sepatu", "celana", "jaket", "tas", "meja", "kursi", "lemari", "ps4", "ps5", "iphone"
]

def parse_price(text: str) -> int:
    numbers = re.sub(r"[^\d]", "", text)
    return int(numbers) if numbers else 0

async def scrape_toco_vga(
    query: str = "vga rtx",
    min_price: int = 800000,
    max_price: int = 6000000,
    max_items: int = 25
):
    encoded_query = urllib.parse.quote(query)
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
        await page.route("**/*.{png,jpg,jpeg,webp,svg,gif,woff,woff2,css}", lambda route: route.abort())
        
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
                        
                if not title:
                    continue
                    
                t_low = title.lower()
                
                # 1. Reject mutlak blacklist non-GPU (sepeda, gundam, dll)
                if any(b in t_low for b in BANNED_NON_GPU):
                    continue
                    
                # 1.5. Reject barang baru / dropshipper (gambar generic)
                if any(k in t_low for k in ["bnib", "brand new", "bnob", "baru garansi", "stok ready", "stok baru"]):
                    continue
                    
                # 2. Wajib lolos regex GPU nyata
                if not GPU_STRICT_REGEX.search(t_low):
                    continue
                    
                price_num = parse_price(price_str)
                norm_title = re.sub(r'[^a-zA-Z0-9]', '', t_low[:30])
                if norm_title in seen_titles:
                    continue
                seen_titles.add(norm_title)
                
                if min_price <= price_num <= max_price:
                    # Ekstraksi Foto Toco
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
                    
            output_file = "toco_vga_deals.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            print(f"[+] Berhasil filter {len(results)} VGA Toco asli ke {output_file}")
            return results
            
        except Exception as e:
            print(f"[-] Error Toco: {e}")
            return []
        finally:
            await browser.close()

if __name__ == "__main__":
    deals = asyncio.run(scrape_toco_vga("vga rtx", min_price=800000, max_price=6000000))
    print(f"Total VGA Toco Valid: {len(deals)}")
    for d in deals[:5]:
        print(f"[{d['price_raw']}] {d['title']} | {d['location']}")
