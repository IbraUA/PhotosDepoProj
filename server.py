from http.server import HTTPServer, BaseHTTPRequestHandler

HOST = '0.0.0.0'
PORT = 8080

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        if self.path == "/about":
            self.wfile.write(b"About page!")
        elif self.path == "/":
            self.wfile.write(b"Main page")


server = HTTPServer((HOST, PORT), Handler)
server.serve_forever()