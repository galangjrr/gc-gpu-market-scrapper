import asyncio
import os
from playwright.async_api import async_playwright

async def setup_login():
    user_data_dir = os.path.abspath("./shopee_session")
    print("==================================================")
    print("[*] MEMBUKA BROWSER LOGIN SHOPEE...")
    print("[*] Browser tidak akan tertutup otomatis.")
    print("[*] Silakan login santai sampai masuk beranda Shopee.")
    print("==================================================")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://shopee.co.id/buyer/login", wait_until="domcontentloaded")
        
        # Tunggu user tekan ENTER di terminal setelah selesai login
        await asyncio.to_thread(input, "\n[>>>] SETELAH BERHASIL LOGIN DI BROWSER, TEKAN 'ENTER' DI SINI UNTUK MENYIMPAN: ")
        
        print("[+] Session Shopee berhasil disimpan permanen di ./shopee_session!")
        await context.close()

if __name__ == "__main__":
    asyncio.run(setup_login())
