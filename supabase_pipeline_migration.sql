-- ============================================================
-- SUPABASE SCHEMA UPDATE: DATA REFINERY PIPELINE
-- Jalankan HANYA bagian ini di SQL Editor (bukan full schema)
-- ============================================================

-- 1. Tabel Raw Bronze: Dump mentah dari scraper tanpa filter ketat
CREATE TABLE IF NOT EXISTS public.raw_scrapes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    price BIGINT DEFAULT 0,
    price_raw TEXT DEFAULT '',
    description TEXT DEFAULT '',
    platform TEXT NOT NULL,
    location TEXT DEFAULT 'Indonesia',
    url TEXT UNIQUE NOT NULL,
    image_url TEXT DEFAULT '',
    source TEXT DEFAULT '',
    scraped_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    refined BOOLEAN DEFAULT false  -- Flag: sudah diproses refiner atau belum
);

CREATE INDEX IF NOT EXISTS idx_raw_scrapes_refined ON public.raw_scrapes(refined);
CREATE INDEX IF NOT EXISTS idx_raw_scrapes_scraped_at ON public.raw_scrapes(scraped_at DESC);

ALTER TABLE public.raw_scrapes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all on raw_scrapes" ON public.raw_scrapes FOR ALL USING (true);

-- 2. Tabel Gold: Hasil olahan refiner yang bersih dan terstruktur
CREATE TABLE IF NOT EXISTS public.gold_deals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    raw_id UUID REFERENCES public.raw_scrapes(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    price BIGINT NOT NULL,
    price_raw TEXT DEFAULT '',
    platform TEXT NOT NULL,
    location TEXT DEFAULT 'Indonesia',
    url TEXT UNIQUE NOT NULL,
    image_url TEXT DEFAULT '',

    -- Spesifikasi terekstrak
    chipset TEXT DEFAULT '',
    brand TEXT DEFAULT 'OEM',
    variant TEXT DEFAULT '',
    vram TEXT DEFAULT '-',
    cooler_type TEXT DEFAULT 'Dual Fan',
    cooler_tier TEXT DEFAULT 'A',

    -- Kondisi unit
    is_negotiable BOOLEAN DEFAULT false,
    box_status TEXT DEFAULT 'UNKNOWN',     -- FULLSET / DUS_POLOS / NO_DUS / UNKNOWN
    seal_status TEXT DEFAULT 'UNKNOWN',    -- UTUH / PERNAH_BUKA / REPASTE / UNKNOWN
    usage_claim TEXT DEFAULT 'UNKNOWN',    -- PRIBADI / MINING / GAMING / UNKNOWN
    physical_flaw TEXT DEFAULT 'NONE',     -- NONE / KARAT / KOTOR / PATAH
    vision_note TEXT DEFAULT '',           -- Catatan dari Gemini Vision (jika ada)

    -- Keputusan refiner
    gold_status TEXT DEFAULT 'PENDING',    -- APPROVED / WARNING_FLAW / REJECTED_LOW_SPEC / REJECTED_JUNK
    reject_reason TEXT DEFAULT '',
    is_steal_candidate BOOLEAN DEFAULT false,
    action_note TEXT DEFAULT '',

    -- Supabase sync
    deal_hash TEXT UNIQUE,
    is_steal_deal BOOLEAN DEFAULT false,
    smart_score INTEGER DEFAULT 0,
    deal_type TEXT DEFAULT 'PENDING',
    action_decision TEXT DEFAULT 'pending',

    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gold_deals_status ON public.gold_deals(gold_status);
CREATE INDEX IF NOT EXISTS idx_gold_deals_chipset ON public.gold_deals(chipset);
CREATE INDEX IF NOT EXISTS idx_gold_deals_price ON public.gold_deals(price);
CREATE INDEX IF NOT EXISTS idx_gold_deals_created_at ON public.gold_deals(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_gold_deals_hash ON public.gold_deals(deal_hash);

ALTER TABLE public.gold_deals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all on gold_deals" ON public.gold_deals FOR ALL USING (true);

-- 3. Tambah kolom spotter_config ke bot_commands (filter kustom dari web)
ALTER TABLE public.bot_commands ADD COLUMN IF NOT EXISTS spotter_config JSONB DEFAULT NULL;
-- Format spotter_config:
-- {
--   "min_price": 1500000,
--   "max_price": 6000000,
--   "green_keywords": ["mulus", "garansi", "pribadi"],
--   "red_keywords": ["rusak", "matot", "kanibal"]
-- }

-- 4. Realtime untuk gold_deals
ALTER PUBLICATION supabase_realtime ADD TABLE public.raw_scrapes;
ALTER PUBLICATION supabase_realtime ADD TABLE public.gold_deals;
