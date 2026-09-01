import asyncio
import json
import os
import threading
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from hunter import run_sniper_round, init_db
from generate_dashboard import generate_dashboard

PORT = 5000
STATUS_FILE = "bot_status.json"

bot_state = {
    "status": "STOPPED",  # IDLE, SCANNING, SLEEPING, STOPPED
    "last_scan_time": "-",
    "next_scan_timestamp": 0,
    "interval_minutes": 10,
    "last_result_summary": "Belum ada pemindaian",
    "is_busy": False
}

def save_status():
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(bot_state, f, indent=2)

def set_state(status, busy=False, summary=None):
    bot_state["status"] = status
    bot_state["is_busy"] = busy
    if summary:
        bot_state["last_result_summary"] = summary
    save_status()

# Background Worker Thread
def background_scheduler():
    global bot_state
    init_db()
    
    while True:
        try:
            # 1. Start Scan
            set_state("SCANNING", busy=True, summary="Sedang memindai Tokopedia, FB & Toco...")
            current_time_str = time.strftime("%H:%M:%S WIB")
            bot_state["last_scan_time"] = current_time_str
            save_status()

            # Jalankan sniper
            asyncio.run(run_sniper_round())
            
            # Regenerate dashboard HTML
            generate_dashboard()

            # 2. Sleeping phase
            interval_sec = bot_state["interval_minutes"] * 60
            bot_state["next_scan_timestamp"] = int(time.time()) + interval_sec
            set_state("SLEEPING", busy=False, summary=f"Selesai pada {current_time_str}. Siap scan berikutnya.")

            # Tidur dengan interval
            for _ in range(interval_sec):
                if bot_state.get("force_trigger"):
                    bot_state["force_trigger"] = False
                    break
                time.sleep(1)

        except Exception as e:
            set_state("ERROR", busy=False, summary=f"Error: {str(e)}")
            time.sleep(10)

def trigger_manual_scan():
    if bot_state.get("is_busy"):
        return False, "Bot sedang sibuk melakukan scan"
    bot_state["force_trigger"] = True
    return True, "Scan berhasil dipicu"

class DashboardRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            self.path = "/dashboard.html"
            return super().do_GET()
            
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            # Hitung sisa detik
            now = int(time.time())
            remaining = max(0, bot_state["next_scan_timestamp"] - now) if bot_state["status"] == "SLEEPING" else 0
            
            payload = {
                **bot_state,
                "remaining_seconds": remaining
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return
            
        super().do_GET()

    def do_POST(self):
        if self.path == "/api/trigger-scan":
            success, msg = trigger_manual_scan()
            self.send_response(200 if success else 409)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "message": msg}).encode("utf-8"))
            return
            
        self.send_response(404)
        self.end_headers()

def start_server():
    # Pastikan dashboard awal sudah ada
    generate_dashboard()
    
    # Jalankan background scheduler di thread terpisah
    worker_thread = threading.Thread(target=background_scheduler, daemon=True)
    worker_thread.start()
    
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, DashboardRequestHandler)
    print(f"============================================================")
    print(f"[*] SERVER VGA HUNTER CONTROL CENTER RUNNING DI:")
    print(f"[*] http://localhost:{PORT}")
    print(f"[*] Tekan Ctrl+C untuk berhenti")
    print(f"============================================================")
    
    webbrowser.open(f"http://localhost:{PORT}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server dimatikan.")
        httpd.server_close()

if __name__ == "__main__":
    start_server()
