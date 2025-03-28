# Start an HTTP server for serving data
from http.server import SimpleHTTPRequestHandler
import socketserver
import os

PORT = 8000
DIRECTORY = "./"

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        SimpleHTTPRequestHandler.end_headers(self)

os.chdir(DIRECTORY)
Handler = CORSRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving HTTP on port {PORT}")
    httpd.serve_forever()
