#!/usr/bin/env python3
"""
AutoCare Pro — zero-dependency development server (Python fallback).

Serves this folder over http:// so the PWA layer (service worker, install
prompt, offline cache) can run — browsers refuse to register a service worker
on file://.

    python server.py

Picks the first free port from 5500 upward, opens the default browser and runs
until Ctrl+C. Standard library only; no pip install.
"""

import http.server
import os
import socket
import socketserver
import sys
import threading
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
START_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
MAX_TRIES = 20


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves from the project folder and keeps the service worker fresh."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        # Without this the browser can pin an old service worker forever.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):  # keep the console readable
        pass


def free_port(start):
    for port in range(start, start + MAX_TRIES):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def main():
    port = free_port(START_PORT)
    url = f"http://localhost:{port}/index.html"

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print("")
        print("   AUTOCARE PRO  //  Smart Vehicle Maintenance System")
        print("   ---------------------------------------------------")
        print(f"   Running at   {url}")
        print("   Stop server  Ctrl + C")
        print("")
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n   Server stopped.\n")


if __name__ == "__main__":
    main()
