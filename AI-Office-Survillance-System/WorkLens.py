#!/usr/bin/env python3
# WorkLens Command Center - local launcher. Serves the dashboard on http://localhost
# (a "secure context" so the browser allows the webcam). Zero installs, stdlib only.
import http.server, socketserver, webbrowser, threading, os
DIR = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(DIR, "WorkLens-Command-Center.html")
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/WorkLens-Command-Center.html", "/index.html"):
            try:
                data = open(HTML, "rb").read()
            except Exception:
                self.send_error(404); return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data)
        else:
            self.send_error(404)
    def log_message(self, *a): pass
def main():
    srv = None; port = None
    for p in [8777, 8778, 8000, 8080, 0]:
        try:
            srv = socketserver.ThreadingTCPServer(("127.0.0.1", p), H)
            port = srv.server_address[1]; break
        except OSError:
            continue
    url = "http://localhost:%d/WorkLens-Command-Center.html" % port
    print("=" * 54)
    print("  WorkLens Command Center is running!")
    print("=" * 54)
    print("  Open:  " + url)
    print("  The browser will open automatically.")
    print("  Allow the CAMERA when the browser asks -> live feed + AI detection.")
    print("  Keep THIS window open. Close it to stop. (Ctrl+C)")
    print("=" * 54)
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
if __name__ == "__main__":
    main()
