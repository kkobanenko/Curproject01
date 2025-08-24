#!/usr/bin/env python3
"""
Очень простой тестовый HTTP сервер
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"Получен запрос: {self.path}")
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            "message": "Hello from simple test API!",
            "path": self.path,
            "timestamp": time.time()
        }
        print(f"Отправляю ответ: {response}")
        self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

if __name__ == "__main__":
    try:
        print("Запускаю простой тестовый API на порту 8081...")
        server = HTTPServer(('0.0.0.0', 8081), SimpleHandler)
        print(f"API запущен на 0.0.0.0:8081")
        print(f"Готов принимать запросы...")
        server.serve_forever()
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
