"""
proxy.py — простой прокси-сервер для сокрытия API ключа vsegpt.
Запускать: python proxy.py
Сайт обращается к http://localhost:8080/chat вместо vsegpt напрямую.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.error
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("VSEGPT_API_KEY")
PORT = 8080

# Разрешённые домены (твой сайт на GitHub Pages)
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "https://YOUR_USERNAME.github.io",  # ← замени на свой
]

class ProxyHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def do_OPTIONS(self):
        """Preflight CORS запрос."""
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path != "/chat":
            self.send_response(404)
            self.end_headers()
            return

        # Читаем тело запроса
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
        except Exception:
            self.send_response(400)
            self._cors_headers()
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON"}')
            return

        # Отправляем запрос в vsegpt с нашим ключом
        req = urllib.request.Request(
            "https://api.vsegpt.ru/v1/chat/completions",
            data=json.dumps(data).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = resp.read()
                self.send_response(200)
                self._cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(result)

        except urllib.error.HTTPError as e:
            error_body = e.read()
            self.send_response(e.code)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error_body)

        except Exception as e:
            self.send_response(500)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _cors_headers(self):
        origin = self.headers.get("Origin", "")
        if any(origin.startswith(o) for o in ALLOWED_ORIGINS):
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


if __name__ == "__main__":
    if not API_KEY:
        print("❌ VSEGPT_API_KEY не найден в .env файле!")
        exit(1)

    server = HTTPServer(("0.0.0.0", PORT), ProxyHandler)
    print(f"✅ Прокси запущен на http://localhost:{PORT}")
    print(f"   Ключ: {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"   Остановить: Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⛔ Прокси остановлен")
