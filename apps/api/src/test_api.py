#!/usr/bin/env python3
"""
Простой тестовый HTTP сервер
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import socket

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"Получен запрос: {self.path}")
        if self.path == "/health":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "service": "test-api",
                "timestamp": time.time(),
                "path": self.path,
                "client": self.client_address[0]
            }
            print(f"Отправляю ответ: {response}")
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            response = f"Hello from test API! Path: {self.path}, Client: {self.client_address[0]}"
            print(f"Отправляю ответ: {response}")
            self.wfile.write(response.encode())
    
    def log_message(self, format, *args):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

if __name__ == "__main__":
    try:
        # Явно привязываемся ко всем интерфейсам
        server = HTTPServer(('0.0.0.0', 8080), TestHandler)
        print(f"Test API server started on 0.0.0.0:8080")
        print(f"Server socket: {server.socket}")
        print(f"Server address: {server.server_address}")
        
        # Проверяем, что сервер действительно слушает
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        result = sock.connect_ex(('0.0.0.0', 8080))
        print(f"Port 8080 connection test result: {result}")
        sock.close()
        
        server.serve_forever()
    except Exception as e:
        print(f"Ошибка запуска сервера: {e}")
        import traceback
        traceback.print_exc()
