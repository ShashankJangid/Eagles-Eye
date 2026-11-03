import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            "name": "Eagle's Eye AI",
            "status": "online",
            "version": "2.5"
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))
