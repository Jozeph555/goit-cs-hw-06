"""
Модуль реалізації простого веб-додатку з обробкою повідомлень через сокет-сервер.
Забезпечує маршрутизацію HTTP-запитів, обробку статичних файлів
та збереження повідомлень в MongoDB.
"""


from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import socket
import urllib.parse
import threading
from datetime import datetime
from pathlib import Path
try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:
    print("Помилка: Будь ласка, встановіть pymongo: pip install pymongo")
    raise


# Конфігурація
HOST = '0.0.0.0'
HTTP_PORT = 3000
SOCKET_PORT = 5000
MONGO_URL = 'mongodb://mongo:27017'
DB_NAME = 'messages_db'
COLLECTION_NAME = 'messages'


# Шляхи до директорій
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / 'static'
TEMPLATES_DIR = BASE_DIR / 'templates'


class SocketServer(threading.Thread):
    """Socket-сервер для обробки повідомлень"""
    def __init__(self, host=HOST, port=SOCKET_PORT):
        """Ініціалізація сокет-сервера"""
        super().__init__()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))
        self.socket.listen(1)
        self.mongo_client = MongoClient(MONGO_URL)
        self.db = self.mongo_client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]
        print(f"Socket server listening on {host}:{port}")
        self.daemon = True

    def run(self):
        """Запускає сокет-сервер"""
        while True:
            conn, addr = self.socket.accept()
            print(f"Connection from {addr}")
            try:
                data = conn.recv(1024).decode()
                if data:
                    message = json.loads(data)
                    message['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    self.collection.insert_one(message)
                    print(f"Saved message: {message}")
            except (json.JSONDecodeError, PyMongoError, socket.error) as error:
                print(f"Error handling message: {error}")
            finally:
                conn.close()


class HttpHandler(BaseHTTPRequestHandler):
    """Обробник HTTP-запитів"""
    def do_GET(self):  # pylint: disable=invalid-name
        """Обробка GET-запитів"""
        if self.path == '/':
            self.send_html_file('index.html')
        elif self.path == '/message.html':
            self.send_html_file('message.html')
        elif self.path.startswith(('/style.css', '/logo.png')):
            self.send_static_file(self.path[1:])
        else:
            self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        """Відправка HTML-файлів"""
        file_path = TEMPLATES_DIR / filename
        try:
            with open(file_path, 'rb') as file:
                content = file.read()
            self.send_response(status)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_html_file('error.html', 404)

    def send_static_file(self, filename):
        """Відправка статичних файлів"""
        file_path = STATIC_DIR / filename
        try:
            with open(file_path, 'rb') as file:
                content = file.read()
            self.send_response(200)
            content_type = 'text/css' if filename.endswith('.css') else 'image/png'
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_html_file('error.html', 404)

    def do_POST(self):  # pylint: disable=invalid-name
        """Обробка POST-запитів"""
        if self.path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode()
            params = urllib.parse.parse_qs(post_data)

            message = {
                'username': params.get('username', [''])[0],
                'message': params.get('message', [''])[0]
            }

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', SOCKET_PORT))
                sock.send(json.dumps(message).encode())
            except (ConnectionError, socket.error) as error:
                print(f"Error sending to socket: {error}")
            finally:
                sock.close()

            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()


def main():
    """Головна функція програми"""
    # Запуск сокет-сервера в окремому потоці
    socket_server = SocketServer()
    socket_server.start()

    # Запуск HTTP-сервера
    server_address = (HOST, HTTP_PORT)
    httpd = HTTPServer(server_address, HttpHandler)
    print(f"HTTP server running on {HOST}:{HTTP_PORT}")
    httpd.serve_forever()


if __name__ == '__main__':
    main()
