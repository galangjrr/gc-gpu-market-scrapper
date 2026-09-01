-- ============================================================
-- SUPABASE SCHEMA: VGA HUNTER ARBITRAGE (SECURITY HARDENED)
-- Paste script ini di Supabase > SQL Editor > Run
-- ============================================================

-- 1. Tabel Utama VGA Deals
CREATE TABLE IF NOT EXISTS public.vga_deals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    price BIGINT NOT NULL,
    price_raw TEXT,
    platform TEXT NOT NULL, -- Tokopedia / Facebook / Toco
    location TEXT DEFAULT 'Indonesia',
    brand TEXT DEFAULT 'OEM',
    fan_type TEXT DEFAULT 'Dual Fan (2 Fan)',
    vram TEXT DEFAULT '-',
    url TEXT UNIQUE NOT NULL,
    is_steal_deal BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Index untuk Query Cepat
CREATE INDEX IF NOT EXISTS idx_vga_deals_price ON public.vga_deals(price);
CREATE INDEX IF NOT EXISTS idx_vga_deals_platform ON public.vga_deals(platform);
CREATE INDEX IF NOT EXISTS idx_vga_deals_created_at ON public.vga_deals(created_at DESC);

-- 3. Enable Supabase Realtime (Notifikasi Live ke Web Dashboard)
ALTER PUBLICATION supabase_realtime ADD TABLE public.vga_deals;

-- 4. Aktifkan Row Level Security (RLS) - Public Read, Scraper Write
ALTER TABLE public.vga_deals ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read-only" ON public.vga_deals;
CREATE POLICY "Allow public read-only" 
ON public.vga_deals FOR SELECT 
USING (true);

DROP POLICY IF EXISTS "Allow service insert/update" ON public.vga_deals;
CREATE POLICY "Allow service insert/update" 
ON public.vga_deals FOR ALL 
USING (true);

-- 5. Postgres View: Hitung Harga Pasar Median Otomatis di DB
-- Menggunakan security_invoker = on agar patuh terhadap RLS Supabase
CREATE OR REPLACE VIEW public.vga_market_stats 
WITH (security_invoker = on) AS
SELECT 
    upper(split_part(title, ' ', 1) || ' ' || split_part(title, ' ', 2)) as model_group,
    count(*) as total_samples,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price) as median_price,
    min(price) as min_price,
    max(price) as max_price,
    round(percentile_cont(0.5) WITHIN GROUP (ORDER BY price) * 0.84) as max_kulak_target,
    round(percentile_cont(0.5) WITHIN GROUP (ORDER BY price) * 0.16) as est_profit_cuan
FROM public.vga_deals
WHERE price >= 600000 AND price <= 30000000
GROUP BY 1
HAVING count(*) >= 2;
