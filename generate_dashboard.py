import json
import os
import re
import statistics
import webbrowser

ALL_TARGET_MODELS = [
    # Nvidia RTX 40 Series
    "rtx 4090", "rtx 4080 super", "rtx 4080", "rtx 4070 ti super", "rtx 4070 ti",
    "rtx 4070 super", "rtx 4070", "rtx 4060 ti", "rtx 4060",
    
    # Nvidia RTX 30 Series
    "rtx 3090 ti", "rtx 3090", "rtx 3080 ti", "rtx 3080", "rtx 3070 ti",
    "rtx 3070", "rtx 3060 ti", "rtx 3060", "rtx 3050",
    
    # Nvidia RTX 20 Series
    "rtx 2080 ti", "rtx 2080 super", "rtx 2080", "rtx 2070 super",
    "rtx 2070", "rtx 2060 super", "rtx 2060",
    
    # Nvidia GTX 16 & 10 Series
    "gtx 1660 super", "gtx 1660 ti", "gtx 1660", "gtx 1650 super", "gtx 1650",
    "gtx 1080 ti", "gtx 1080", "gtx 1070 ti", "gtx 1070", "gtx 1060",
    
    # AMD Radeon RX 7000 Series
    "rx 7900 xtx", "rx 7900 xt", "rx 7800 xt", "rx 7700 xt", "rx 7600 xt", "rx 7600",
    
    # AMD Radeon RX 6000 Series
    "rx 6950 xt", "rx 6900 xt", "rx 6800 xt", "rx 6800", "rx 6750 xt", "rx 6700 xt",
    "rx 6650 xt", "rx 6600 xt", "rx 6600", "rx 6500 xt",
    
    # AMD Radeon RX 5000 Series
    "rx 5700 xt", "rx 5700", "rx 5600 xt", "rx 5500 xt",
    
    # Intel Arc Series
    "arc a770", "arc a750", "arc a580", "arc b580"
]

# KATA KUNCI SAMPAH & SPAREPART YANG HARUS DIBUANG DARI KATALOG
NEGATIVE_JUNK_KEYWORDS = [
    "gundam", "gunpla", "bandai", "mokit", "figure", "figurine", "model kit", "tamiya",
    "part ", "part -", "kanibal", "matot", "mati total", "mati", "artefak", "no display",
    "bangkai", "rusak", "servisan", "short", "hangus", "hanya dus", "box saja", "kotak saja",
    "dus saja", "cooler only", "heatsink", "fan replacement", "kipas saja", "backplate",
    "bracket", "kabel riser", "riser card", "kabel pcie", "dock egpu", "casing egpu",
    "dummy plug", "converter", "thermal pad", "baut", "gt 710", "gt 730", "gt 610", "gt 210"
]

SAFE_PHRASES = [
    "no minus", "no artefak", "no display port", "no kendala", "no error",
    "bukan matot", "bukan servisan", "dijamin normal", "lancar jaya", "tested normal"
]

def is_clean_gpu(title: str, price: int) -> bool:
    if price < 800000:
        return False
        
    t_clean = title.lower()
    for safe in SAFE_PHRASES:
        t_clean = t_clean.replace(safe, "")
        
    for junk in NEGATIVE_JUNK_KEYWORDS:
        if junk in t_clean:
            return False
            
    # Wajib lolos regex model GPU presisi
    from scraper_toco import GPU_STRICT_REGEX
    return bool(GPU_STRICT_REGEX.search(t_clean))

def parse_gpu_specs(title: str) -> dict:
    t_low = title.lower()
    
    brands = [
        ("asus", "ASUS"), ("rog", "ASUS ROG"), ("tuf", "ASUS TUF"),
        ("msi", "MSI"), ("gigabyte", "GIGABYTE"), ("aorus", "AORUS"),
        ("evga", "EVGA"), ("zotac", "ZOTAC"), ("colorful", "COLORFUL"),
        ("igame", "COLORFUL iGame"), ("galax", "GALAX"), ("palit", "PALIT"),
        ("sapphire", "SAPPHIRE"), ("powercolor", "POWERCOLOR"), ("asrock", "ASROCK"),
        ("inno3d", "INNO3D"), ("gainward", "GAINWARD"), ("leadtek", "LEADTEK"),
        ("manli", "MANLI"), ("pny", "PNY"), ("xfx", "XFX")
    ]
    detected_brand = "OEM / Custom"
    for b_key, b_name in brands:
        if b_key in t_low:
            detected_brand = b_name
            break
            
    fan_type = "Dual Fan (2 Fan)"
    if any(w in t_low for w in ["3 fan", "3fan", "triple fan", "tri fan", "trio", "3x", "ventus 3x", "strix", "suprim", "red devil", "taichi", "vision"]):
        fan_type = "Triple Fan (3 Fan)"
    elif any(w in t_low for w in ["1 fan", "1fan", "single fan", "itx", "mini", "stormx", "phoenix", "aero itx", "solo", "compact"]):
        fan_type = "Single Fan / ITX"
    elif any(w in t_low for w in ["2 fan", "2fan", "dual fan", "twin", "2x", "dual", "ventus 2x", "pulse", "fighter"]):
        fan_type = "Dual Fan (2 Fan)"
        
    # Cocokkan model utama
    matched_model = "-"
    for m in ALL_TARGET_MODELS:
        if m in t_low:
            matched_model = m.upper()
            break
            
    vram_match = re.search(r"(\d+)\s*(?:gb|g)\b", t_low)
    vram = f"{vram_match.group(1)}GB" if vram_match else "-"
    
    return {
        "brand": detected_brand,
        "fan_type": fan_type,
        "model_tag": matched_model,
        "vram": vram
    }

def generate_dashboard():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    files = {
        "Tokopedia": os.path.join(base_dir, "tokped_vga_deals.json"),
        "Facebook": os.path.join(base_dir, "fb_vga_deals.json"),
        "Toco": os.path.join(base_dir, "toco_vga_deals.json")
    }
    
    all_deals = []
    seen_urls = set()
    seen_title_prices = set()
    
    for platform, f_name in files.items():
        if os.path.exists(f_name):
            try:
                with open(f_name, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    for it in items:
                        url = it.get("url", "")
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                        
                        title = it.get("title", "")
                        price = it.get("price", 0)
                        
                        # Filter ketat: HANYA MASUKKAN VGA NORMAL YANG LAYAK
                        if not is_clean_gpu(title, price):
                            continue
                            
                        # DEDUPLIKASI SPAM DROPSHIPPER (Judul + Harga Sama Persis)
                        norm_title = re.sub(r'[^a-zA-Z0-9]', '', title.lower()[:30])
                        dup_key = f"{platform}_{norm_title}_{price}"
                        if dup_key in seen_title_prices:
                            continue
                        seen_title_prices.add(dup_key)
                            
                        it["platform"] = platform
                        specs = parse_gpu_specs(title)
                        it.update(specs)
                        all_deals.append(it)
            except Exception:
                pass
                
    market_matrix = {}
    chart_labels = []
    chart_market_prices = []
    chart_snipe_prices = []

    for model in ALL_TARGET_MODELS:
        prices = [d["price"] for d in all_deals if model in d.get("title", "").lower() and d["price"] >= 800000]
        if len(prices) >= 1:
            med = int(statistics.median(prices))
            min_p = min(prices)
            max_p = max(prices)
            max_kulak = int(med * 0.84)
            cuan = med - max_kulak
            
            m_key = model.upper()
            market_matrix[m_key] = {
                "model": m_key,
                "samples": len(prices),
                "median": med,
                "min_price": min_p,
                "max_price": max_p,
                "max_kulak": max_kulak,
                "cuan": cuan
            }
            
            if len(prices) >= 2 and len(chart_labels) < 10:
                chart_labels.append(m_key)
                chart_market_prices.append(med)
                chart_snipe_prices.append(max_kulak)

    # Tandai Steal Deal & Hitung Potensi Margin Tiap Item
    for deal in all_deals:
        m_tag = deal.get("model_tag")
        if m_tag in market_matrix:
            median_p = market_matrix[m_tag]["median"]
            max_k = market_matrix[m_tag]["max_kulak"]
            deal["is_steal_deal"] = deal["price"] <= max_k
            deal["margin_est"] = median_p - deal["price"]
            deal["market_median"] = median_p
        else:
            deal["is_steal_deal"] = False
            deal["margin_est"] = 0
            deal["market_median"] = 0

    # Urutkan: Steal Deal paling cuan di urutan paling atas!
    all_deals.sort(key=lambda x: (not x.get("is_steal_deal", False), -x.get("margin_est", 0)))

    deals_json_str = json.dumps(all_deals, ensure_ascii=False)
    matrix_json_str = json.dumps(market_matrix, ensure_ascii=False)
    chart_labels_str = json.dumps(chart_labels)
    chart_market_str = json.dumps(chart_market_prices)
    chart_snipe_str = json.dumps(chart_snipe_prices)

    html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VGA Hunter Pro • Clean Curated Edition</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;500;600;700;800&display=swap');
    body {{
      background-color: #F0F3F7;
      color: #212121;
      font-family: 'Open Sans', system-ui, -apple-system, sans-serif;
      -webkit-font-smoothing: antialiased;
    }}
    .card-tokped {{
      background: #FFFFFF;
      border: 1px solid #E5E7EB;
      box-shadow: 0 1px 4px rgba(141, 150, 170, 0.08);
      border-radius: 12px;
    }}
    .tab-btn.active {{
      background-color: #03AC0E;
      color: #FFFFFF;
      border-color: #03AC0E;
    }}
  </style>
</head>
<body class="min-h-screen">
  
  <!-- NAVBAR -->
  <header class="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl bg-[#03AC0E] flex items-center justify-center text-white text-lg font-black shadow-sm">
          <i class="fa-solid fa-microchip"></i>
        </div>
        <div>
          <div class="font-extrabold text-base sm:text-lg text-slate-800 tracking-tight flex items-center gap-1.5">
            <span>VGA</span><span class="text-[#03AC0E]">Hunter</span>
            <span class="text-[10px] font-bold px-1.5 py-0.5 bg-emerald-50 text-[#03AC0E] rounded border border-emerald-200 ml-1">CLEAN CURATED</span>
          </div>
          <p class="text-[11px] text-slate-500 font-medium hidden sm:block">100% Bebas Sampah Kanibalan / Matot / Aksesoris</p>
        </div>
      </div>
      
      <div class="flex items-center gap-2 sm:gap-4">
        <div class="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold" id="botStatusPill">
          <span class="w-2.5 h-2.5 rounded-full bg-slate-400" id="botStatusDot"></span>
          <span class="text-slate-700" id="botStatusText">Menghubungkan...</span>
          <span class="text-slate-400 font-mono text-[11px] border-l border-slate-300 pl-2 hidden md:inline" id="botCountdown">--:--</span>
        </div>

        <button onclick="triggerBotScan()" id="btnTriggerScan" class="px-3.5 py-1.5 bg-[#03AC0E] hover:bg-[#028A0B] text-white rounded-lg text-xs font-bold flex items-center gap-1.5 transition shadow-sm">
          <i class="fa-solid fa-bolt" id="btnIcon"></i>
          <span id="btnText">Scan Sekarang</span>
        </button>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

    <!-- KPI STATS -->
    <section class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="card-tokped p-4">
        <div class="text-xs font-semibold text-slate-500">Unit Normal Terverifikasi</div>
        <div class="text-2xl sm:text-3xl font-extrabold mt-1 text-slate-800" id="stat-total">0</div>
        <div class="text-xs text-[#03AC0E] font-semibold mt-1">Bebas Part Kanibal</div>
      </div>
      <div class="card-tokped p-4">
        <div class="text-xs font-semibold text-slate-500">Peluang Cuan (Steal Deals)</div>
        <div class="text-2xl sm:text-3xl font-extrabold mt-1 text-[#03AC0E]" id="stat-steal">0 Unit</div>
        <div class="text-xs text-emerald-600 font-semibold mt-1">Di Bawah Batas Kulak</div>
      </div>
      <div class="card-tokped p-4">
        <div class="text-xs font-semibold text-slate-500">Filter Sampah Aktif</div>
        <div class="text-xl sm:text-2xl font-extrabold mt-1 text-blue-600">Auto-Filtered</div>
        <div class="text-xs text-slate-500 mt-1">Matot / Box / Kabel Dibuang</div>
      </div>
      <div class="card-tokped p-4">
        <div class="text-xs font-semibold text-slate-500">Potensi Margin Tertinggi</div>
        <div class="text-xl sm:text-2xl font-extrabold mt-1 text-orange-600" id="stat-max-margin">+Rp 0</div>
        <div class="text-xs text-slate-500 mt-1">Spread Arbitrase Bersih</div>
      </div>
    </section>

    <!-- DECISION CALCULATOR -->
    <section class="card-tokped p-6 border-l-4 border-l-[#03AC0E]">
      <div class="flex items-center gap-2 mb-2">
        <span class="p-1.5 bg-emerald-50 text-[#03AC0E] rounded-md text-sm"><i class="fa-solid fa-calculator"></i></span>
        <h2 class="text-base font-extrabold text-slate-800">Kalkulator Cek Kelayakan Beli</h2>
      </div>
      <p class="text-xs text-slate-500 mb-5">Pilih model VGA dan tipe fan untuk hitungan batas aman kulak &amp; estimasi profit.</p>

      <div class="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
        <div class="md:col-span-4">
          <label class="block text-xs font-bold text-slate-600 mb-1">Model VGA</label>
          <select id="calcModel" class="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-sm font-semibold text-slate-800 focus:ring-2 focus:ring-[#03AC0E] focus:outline-none">
            <!-- Populated via JS -->
          </select>
        </div>
        <div class="md:col-span-3">
          <label class="block text-xs font-bold text-slate-600 mb-1">Tipe Fan</label>
          <select id="calcFan" class="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-sm font-semibold text-slate-800 focus:ring-2 focus:ring-[#03AC0E] focus:outline-none">
            <option value="triple">Triple Fan (+8% Valuasi)</option>
            <option value="dual" selected>Dual Fan (Standard)</option>
            <option value="single">Single Fan / ITX (-5% Valuasi)</option>
          </select>
        </div>
        <div class="md:col-span-3">
          <label class="block text-xs font-bold text-slate-600 mb-1">Harga Ditawarkan Seller (Rp)</label>
          <input type="number" id="calcPrice" placeholder="Contoh: 3200000" class="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-sm font-semibold text-slate-800 focus:ring-2 focus:ring-[#03AC0E] focus:outline-none">
        </div>
        <div class="md:col-span-2">
          <button onclick="checkViability()" class="w-full py-2 bg-[#03AC0E] hover:bg-[#028A0B] text-white font-bold text-sm rounded-lg transition shadow-sm">
            Cek Kelayakan
          </button>
        </div>
      </div>

      <div id="calcResult" class="hidden mt-4 p-4 rounded-xl text-sm transition"></div>
    </section>

    <!-- BENCHMARK TABLE & CHART -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div class="lg:col-span-7 card-tokped p-5 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-3 pb-3 border-b border-slate-100">
            <h3 class="text-sm font-extrabold text-slate-800 flex items-center gap-2">
              <i class="fa-solid fa-table-list text-[#03AC0E]"></i>
              <span>Batas Harga Kulak &amp; Estimasi Cuan</span>
            </h3>
            <input type="text" id="tableFilter" placeholder="Cari seri..." class="px-2.5 py-1 bg-slate-50 border border-slate-200 rounded text-xs text-slate-700">
          </div>
          <div class="overflow-y-auto max-h-80">
            <table class="w-full text-left text-xs">
              <thead class="bg-slate-50 text-slate-500 uppercase font-bold border-b border-slate-200 sticky top-0">
                <tr>
                  <th class="py-2.5 px-3">Seri GPU</th>
                  <th class="py-2.5 px-3 text-right">Harga Pasar</th>
                  <th class="py-2.5 px-3 text-right text-[#03AC0E]">Max Kulak</th>
                  <th class="py-2.5 px-3 text-right text-orange-600">Estimasi Cuan</th>
                </tr>
              </thead>
              <tbody id="matrixTableBody" class="divide-y divide-slate-100 font-semibold text-slate-700">
                <!-- Populated via JS -->
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="lg:col-span-5 card-tokped p-5 flex flex-col justify-between">
        <div class="flex items-center justify-between mb-2 pb-3 border-b border-slate-100">
          <h3 class="text-sm font-extrabold text-slate-800 flex items-center gap-2">
            <i class="fa-solid fa-chart-column text-blue-600"></i>
            <span>Grafik Sebaran Pasar vs Kulak</span>
          </h3>
        </div>
        <div class="h-80 w-full">
          <canvas id="marketChart"></canvas>
        </div>
      </div>
    </section>

    <!-- CLEAN CURATED LISTINGS FEED -->
    <section class="card-tokped p-6 space-y-4">
      <div class="flex flex-col md:flex-row justify-between md:items-center gap-3 pb-3 border-b border-slate-100">
        <div>
          <h3 class="text-base font-extrabold text-slate-800">Katalog Listing VGA Normal (Tersaring)</h3>
          <p class="text-xs text-slate-500">Unit cacat/kanibal dibersihkan. Steal deal diprioritaskan di baris pertama.</p>
        </div>

        <!-- QUICK TAB FILTERS -->
        <div class="flex items-center gap-2">
          <button onclick="setTab('STEAL')" id="tabSteal" class="tab-btn px-3 py-1.5 bg-slate-100 border border-slate-200 rounded-lg text-xs font-bold text-slate-700 flex items-center gap-1.5 transition">
            <i class="fa-solid fa-fire text-amber-500"></i> Hanya Steal Deals
          </button>
          <button onclick="setTab('ALL')" id="tabAll" class="tab-btn active px-3 py-1.5 bg-slate-100 border border-slate-200 rounded-lg text-xs font-bold text-slate-700 flex items-center gap-1.5 transition">
            Semua VGA Normal
          </button>
        </div>
      </div>

      <!-- FILTER CONTROLS -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <input type="text" id="searchInput" placeholder="Cari nama/kota/brand..." class="bg-slate-50 border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:outline-none">
        <select id="fanFilter" class="bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 font-semibold focus:outline-none">
          <option value="ALL">Semua Tipe Fan</option>
          <option value="Triple Fan">Triple Fan (3 Fan)</option>
          <option value="Dual Fan">Dual Fan (2 Fan)</option>
          <option value="Single Fan">Single Fan / ITX</option>
        </select>
        <select id="brandFilter" class="bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 font-semibold focus:outline-none">
          <option value="ALL">Semua Brand</option>
          <option value="ASUS">ASUS / ROG / TUF</option>
          <option value="MSI">MSI</option>
          <option value="GIGABYTE">GIGABYTE / AORUS</option>
          <option value="SAPPHIRE">SAPPHIRE</option>
          <option value="COLORFUL">COLORFUL</option>
          <option value="ZOTAC">ZOTAC</option>
          <option value="GALAX">GALAX</option>
          <option value="PALIT">PALIT</option>
          <option value="POWERCOLOR">POWERCOLOR</option>
        </select>
        <select id="platformFilter" class="bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 font-semibold focus:outline-none">
          <option value="ALL">Semua Platform</option>
          <option value="Tokopedia">Tokopedia</option>
          <option value="Facebook">Facebook</option>
          <option value="Toco">Toco</option>
        </select>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="listingsGrid">
        <!-- Injected via JS -->
      </div>
    </section>

  </main>

  <script>
    const dealsData = {deals_json_str};
    const matrixData = {matrix_json_str};
    let currentTab = 'ALL';

    // Stats
    document.getElementById('stat-total').innerText = dealsData.length;
    const stealCount = dealsData.filter(d => d.is_steal_deal).length;
    document.getElementById('stat-steal').innerText = stealCount + ' Unit';
    
    let maxMargin = 0;
    dealsData.forEach(d => {{
      if (d.margin_est > maxMargin) maxMargin = d.margin_est;
    }});
    document.getElementById('stat-max-margin').innerText = '+Rp ' + maxMargin.toLocaleString('id-ID');

    // Populate Selector
    const calcSelect = document.getElementById('calcModel');
    const sortedKeys = Object.keys(matrixData).sort();
    for (const m of sortedKeys) {{
      calcSelect.innerHTML += `<option value="${{m}}">${{m}}</option>`;
    }}

    function setTab(tab) {{
      currentTab = tab;
      document.getElementById('tabAll').className = tab === 'ALL' ? 'tab-btn active px-3 py-1.5 bg-[#03AC0E] border border-[#03AC0E] rounded-lg text-xs font-bold text-white transition' : 'tab-btn px-3 py-1.5 bg-slate-100 border border-slate-200 rounded-lg text-xs font-bold text-slate-700 transition';
      document.getElementById('tabSteal').className = tab === 'STEAL' ? 'tab-btn active px-3 py-1.5 bg-[#03AC0E] border border-[#03AC0E] rounded-lg text-xs font-bold text-white transition' : 'tab-btn px-3 py-1.5 bg-slate-100 border border-slate-200 rounded-lg text-xs font-bold text-slate-700 transition';
      renderListings();
    }}

    // Decision Logic
    function checkViability() {{
      const model = document.getElementById('calcModel').value;
      const fan = document.getElementById('calcFan').value;
      const price = parseInt(document.getElementById('calcPrice').value);
      const resBox = document.getElementById('calcResult');

      if (!price || isNaN(price)) return;
      const data = matrixData[model];
      if (!data) return;

      let multiplier = 1.0;
      let fanTag = 'Dual Fan (Standard)';
      if (fan === 'triple') {{
        multiplier = 1.08;
        fanTag = 'Triple Fan (Premium +8%)';
      }} else if (fan === 'single') {{
        multiplier = 0.94;
        fanTag = 'Single Fan / ITX (-6%)';
      }}

      const med = Math.round(data.median * multiplier);
      const maxKulak = Math.round(data.max_kulak * multiplier);
      const profit = med - price;
      const roi = ((profit / price) * 100).toFixed(1);

      resBox.classList.remove('hidden');

      if (price <= maxKulak) {{
        resBox.className = 'mt-4 p-4 rounded-xl border border-emerald-300 bg-emerald-50 text-emerald-900 text-xs flex justify-between items-center';
        resBox.innerHTML = `
          <div>
            <div class="font-extrabold text-sm text-[#03AC0E] flex items-center gap-1.5 mb-1">
              <i class="fa-solid fa-circle-check"></i> SANGAT LAYAK DIBELI (STEAL DEAL) [${{fanTag}}]
            </div>
            <div class="text-slate-600">Harga seller Rp ${{price.toLocaleString('id-ID')}} di bawah batas aman kulak (Rp ${{maxKulak.toLocaleString('id-ID')}}).</div>
          </div>
          <div class="text-right">
            <div class="text-xs text-slate-500 font-bold">Potensi Cuan Bersih</div>
            <div class="text-lg font-black text-[#03AC0E]">+Rp ${{profit.toLocaleString('id-ID')}} <span class="text-xs">(${{roi}}% ROI)</span></div>
          </div>
        `;
      }} else if (price <= med) {{
        const diff = price - maxKulak;
        resBox.className = 'mt-4 p-4 rounded-xl border border-amber-200 bg-amber-50 text-amber-900 text-xs flex justify-between items-center';
        resBox.innerHTML = `
          <div>
            <div class="font-extrabold text-sm text-amber-600 flex items-center gap-1.5 mb-1">
              <i class="fa-solid fa-handshake"></i> MARGIN TIPIS (BISA DINEGO) [${{fanTag}}]
            </div>
            <div class="text-slate-600">Nego turun sekitar Rp ${{diff.toLocaleString('id-ID')}} lagi ke seller agar dapat margin aman.</div>
          </div>
          <div class="text-right">
            <div class="text-xs text-slate-500 font-bold">Sisa Margin</div>
            <div class="text-base font-extrabold text-amber-600">+Rp ${{profit.toLocaleString('id-ID')}}</div>
          </div>
        `;
      }} else {{
        resBox.className = 'mt-4 p-4 rounded-xl border border-red-200 bg-red-50 text-red-800 text-xs';
        resBox.innerHTML = `
          <div class="font-extrabold text-sm text-red-700 flex items-center gap-1.5 mb-1">
            <i class="fa-solid fa-circle-xmark"></i> JANGAN DIBELI (KEMAHALAN) [${{fanTag}}]
          </div>
          <div>Harga Rp ${{price.toLocaleString('id-ID')}} lebih mahal dari estimasi harga pasar (${{model}} median Rp ${{med.toLocaleString('id-ID')}}).</div>
        `;
      }}
    }}

    // Table Matrix
    function renderTable() {{
      const filter = document.getElementById('tableFilter').value.toLowerCase();
      const tBody = document.getElementById('matrixTableBody');
      tBody.innerHTML = '';

      for (const [m, d] of Object.entries(matrixData)) {{
        if (filter && !m.toLowerCase().includes(filter)) continue;
        tBody.innerHTML += `
          <tr class="hover:bg-slate-50 transition">
            <td class="py-2.5 px-3 font-bold text-slate-800">${{d.model}}</td>
            <td class="py-2.5 px-3 text-right text-slate-600">Rp ${{d.median.toLocaleString('id-ID')}}</td>
            <td class="py-2.5 px-3 text-right text-[#03AC0E] font-extrabold">&le; Rp ${{d.max_kulak.toLocaleString('id-ID')}}</td>
            <td class="py-2.5 px-3 text-right text-orange-600 font-bold">+Rp ${{d.cuan.toLocaleString('id-ID')}}</td>
          </tr>
        `;
      }}
    }}
    document.getElementById('tableFilter').addEventListener('input', renderTable);
    renderTable();

    // Chart.js
    const ctx = document.getElementById('marketChart').getContext('2d');
    new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: {chart_labels_str},
        datasets: [
          {{
            label: 'Harga Pasar Normal',
            data: {chart_market_str},
            backgroundColor: '#CBD5E1',
            borderRadius: 4
          }},
          {{
            label: 'Batas Max Kulak',
            data: {chart_snipe_str},
            backgroundColor: '#03AC0E',
            borderRadius: 4
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ color: '#475569', font: {{ size: 10, weight: 'bold' }} }} }}
        }},
        scales: {{
          y: {{
            grid: {{ color: '#F1F5F9' }},
            ticks: {{
              color: '#64748B',
              callback: v => (v / 1000000).toFixed(1) + ' Jt'
            }}
          }},
          x: {{
            grid: {{ display: false }},
            ticks: {{ color: '#334155', font: {{ size: 8, weight: 'bold' }} }}
          }}
        }}
      }}
    }});

    // Render Clean Listings
    function renderListings() {{
      const q = document.getElementById('searchInput').value.toLowerCase();
      const p = document.getElementById('platformFilter').value;
      const b = document.getElementById('brandFilter').value;
      const f = document.getElementById('fanFilter').value;
      const grid = document.getElementById('listingsGrid');
      grid.innerHTML = '';

      const filtered = dealsData.filter(d => {{
        if (currentTab === 'STEAL' && !d.is_steal_deal) return false;
        const matchQ = d.title.toLowerCase().includes(q) || (d.location && d.location.toLowerCase().includes(q));
        const matchP = p === 'ALL' || d.platform === p;
        const matchB = b === 'ALL' || (d.brand && d.brand.toUpperCase().includes(b));
        const matchF = f === 'ALL' || (d.fan_type && d.fan_type.includes(f));
        return matchQ && matchP && matchB && matchF;
      }});

      if (filtered.length === 0) {{
        grid.innerHTML = '<div class="col-span-full text-center py-12 text-slate-400 text-xs font-semibold">Tidak ada unit yang sesuai dengan filter.</div>';
        return;
      }}

      filtered.slice(0, 48).forEach(d => {{
        let badgeColor = 'text-[#03AC0E] bg-emerald-50 border-emerald-200';
        if (d.platform === 'Facebook') badgeColor = 'text-blue-600 bg-blue-50 border-blue-200';
        if (d.platform === 'Toco') badgeColor = 'text-orange-600 bg-orange-50 border-orange-200';

        let fanBadge = 'bg-slate-100 text-slate-700';
        if (d.fan_type && d.fan_type.includes('Triple')) fanBadge = 'bg-purple-50 text-purple-700 border border-purple-200';
        else if (d.fan_type && d.fan_type.includes('Single')) fanBadge = 'bg-amber-50 text-amber-700 border border-amber-200';

        let stealCardHeader = '';
        if (d.is_steal_deal && d.margin_est > 0) {{
          stealCardHeader = `
            <div class="mb-2 px-2.5 py-1 bg-amber-50 border border-amber-200 rounded-lg flex items-center justify-between text-xs">
              <span class="font-extrabold text-amber-700 flex items-center gap-1"><i class="fa-solid fa-fire"></i> STEAL DEAL</span>
              <span class="font-black text-amber-800">Margin: +Rp ${{d.margin_est.toLocaleString('id-ID')}}</span>
            </div>
          `;
        }}
        
        let imgHtml = '';
        if (d.image_url) {{
          imgHtml = `<div class="mb-3 w-full h-32 overflow-hidden rounded-lg bg-slate-100 flex items-center justify-center">
                       <img src="${{d.image_url}}" class="w-full h-full object-cover opacity-90 hover:opacity-100 transition" onerror="this.style.display='none'">
                     </div>`;
        }}

        grid.innerHTML += `
          <div class="card-tokped p-4 flex flex-col justify-between hover:shadow-md transition ${{d.is_steal_deal ? 'border-amber-300 ring-1 ring-amber-200' : ''}}">
            <div>
              ${{stealCardHeader}}
              ${{imgHtml}}
              <div class="flex justify-between items-center mb-2">
                <span class="text-[10px] font-extrabold px-2 py-0.5 rounded border ${{badgeColor}} uppercase">${{d.platform}}</span>
                <span class="text-[10px] font-bold px-2 py-0.5 rounded ${{fanBadge}}">${{d.fan_type || '2 Fan'}}</span>
              </div>
              <h4 class="font-bold text-slate-800 text-xs line-clamp-2 leading-relaxed" title="${{d.title}}">${{d.title}}</h4>
              <div class="flex items-center gap-2 mt-2 text-[11px] text-slate-500 font-medium">
                <span class="px-1.5 py-0.5 bg-slate-100 rounded text-[10px] font-semibold text-slate-600">${{d.brand || 'OEM'}}</span>
                <span class="truncate max-w-[120px]"><i class="fa-solid fa-location-dot text-slate-400"></i> ${{d.location || 'Indonesia'}}</span>
              </div>
            </div>
            <div class="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
              <div>
                <div class="text-[10px] text-slate-400 font-semibold">Harga</div>
                <div class="font-extrabold text-sm text-[#03AC0E]">${{d.price_raw || 'Rp ' + d.price.toLocaleString('id-ID')}}</div>
              </div>
              <a href="${{d.url}}" target="_blank" class="px-3 py-1.5 bg-[#03AC0E] hover:bg-[#028A0B] text-white text-xs font-bold rounded-lg transition shadow-sm">
                Beli / Chat &rarr;
              </a>
            </div>
          </div>
        `;
      }});
    }}

    document.getElementById('searchInput').addEventListener('input', renderListings);
    document.getElementById('platformFilter').addEventListener('change', renderListings);
    document.getElementById('brandFilter').addEventListener('change', renderListings);
    document.getElementById('fanFilter').addEventListener('change', renderListings);
    renderListings();

    // LIVE POLLER
    let wasScanning = false;
    async function pollBotStatus() {{
      try {{
        const res = await fetch('/api/status');
        if (!res.ok) throw new Error('Unreachable');
        const data = await res.json();

        const dot = document.getElementById('botStatusDot');
        const text = document.getElementById('botStatusText');
        const count = document.getElementById('botCountdown');
        const btn = document.getElementById('btnTriggerScan');
        const btnIcon = document.getElementById('btnIcon');
        const btnText = document.getElementById('btnText');

        if (data.status === 'SCANNING') {{
          wasScanning = true;
          dot.className = 'w-2.5 h-2.5 rounded-full bg-amber-500 animate-ping';
          text.innerText = 'Sedang Scanning...';
          count.innerText = 'RUNNING';
          btn.disabled = true;
          btnIcon.className = 'fa-solid fa-spinner fa-spin';
          btnText.innerText = 'Scanning...';
        }} else if (data.status === 'SLEEPING') {{
          if (wasScanning) {{
            wasScanning = false;
            location.reload();
          }}
          dot.className = 'w-2.5 h-2.5 rounded-full bg-[#03AC0E]';
          text.innerText = 'Standby (Tidur 10m)';
          btn.disabled = false;
          btnIcon.className = 'fa-solid fa-bolt';
          btnText.innerText = 'Scan Sekarang';

          const mins = Math.floor(data.remaining_seconds / 60);
          const secs = data.remaining_seconds % 60;
          count.innerText = 'Scan berikutnya: ' + String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
        }}
      }} catch (err) {{}}
    }}

    async function triggerBotScan() {{
      const btn = document.getElementById('btnTriggerScan');
      btn.disabled = true;
      try {{
        const res = await fetch('/api/trigger-scan', {{ method: 'POST' }});
        const data = await res.json();
        if (data.success) pollBotStatus();
      }} catch (err) {{}}
    }}

    setInterval(pollBotStatus, 2000);
    pollBotStatus();
  </script>
</body>
</html>
"""

    dashboard_path = os.path.join(base_dir, "dashboard.html")
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"[+] Clean Curated Dashboard updated: {dashboard_path}")
    return dashboard_path

if __name__ == "__main__":
    path = generate_dashboard()
    webbrowser.open(f"file:///{path}")
