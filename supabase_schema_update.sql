-- FASE 5: UPDATE SCHEMA UNTUK FITUR TRASH & REMOTE CONTROL
ALTER TABLE public.vga_deals ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE public.vga_deals ADD COLUMN IF NOT EXISTS deal_hash TEXT;
ALTER TABLE public.vga_deals ADD COLUMN IF NOT EXISTS action_decision TEXT DEFAULT 'pending'; -- pending, trashed, buy
ALTER TABLE public.vga_deals ADD COLUMN IF NOT EXISTS smart_score INTEGER DEFAULT 0;
ALTER TABLE public.vga_deals ADD COLUMN IF NOT EXISTS deal_type TEXT;

-- Tambahkan UNIQUE constraint ke deal_hash untuk mencegah duplicate spam (judul + harga sama persis)
CREATE UNIQUE INDEX IF NOT EXISTS idx_vga_deals_hash ON public.vga_deals(deal_hash);

-- Perbarui RLS untuk web remote agar anonim (dari dashboard Vercel) bisa UPDATE
DROP POLICY IF EXISTS "Allow anon update action" ON public.vga_deals;
CREATE POLICY "Allow anon update action" ON public.vga_deals 
    FOR UPDATE 
    USING (true)
    WITH CHECK (true);
