"""
scrapers/__init__.py — Shared Browser Manager.
Satu Chromium instance untuk seluruh scan round. Hemat RAM 70%, zero zombie.
"""
from playwright.async_api import async_playwright


# Route handler: blokir aset berat (gambar, font, css, media)
async def _block_heavy_assets(route):
    if route.request.resource_type in ("image", "media", "font", "stylesheet"):
        await route.abort()
    else:
        await route.continue_()


class BrowserManager:
    """
    Lifecycle manager untuk 1 Chromium instance.
    Buka di awal round, pakai berulang, tutup di akhir round.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None

    async def start(self):
        """Launch 1 Chromium headless instance."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
                "--blink-settings=imagesEnabled=false",
            ],
        )
        print("[*] Browser Chromium shared instance launched")

    async def new_context(self, **kwargs):
        """
        Buat context baru (isolated cookies/session) dengan route blocker.
        Return (context, page).
        """
        defaults = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "viewport": {"width": 1366, "height": 900},
            "locale": "id-ID",
        }
        defaults.update(kwargs)

        context = await self._browser.new_context(**defaults)
        page = await context.new_page()
        await page.route("**/*", _block_heavy_assets)
        return context, page

    async def close(self):
        """Tutup browser dan playwright. Dipanggil di akhir round."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        print("[*] Browser Chromium shared instance closed")

    @property
    def is_running(self) -> bool:
        return self._browser is not None and self._browser.is_connected()


async def fetch_item_description(page, url: str) -> str:
    """
    Stage 2 Scraper: Membuka URL listing dan mengambil teks body mentah.
    Sangat ringan karena asset berat sudah diblokir oleh BrowserManager.
    """
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)
        body_text = await page.locator("body").inner_text(timeout=5000)
        return body_text
    except Exception as e:
        print(f"[-] Gagal fetch deskripsi {url}: {e}")
        return ""
