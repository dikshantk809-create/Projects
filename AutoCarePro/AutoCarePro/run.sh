#!/usr/bin/env bash
# AutoCare Pro - launcher for macOS and Linux.
# Run:  ./run.sh          (macOS: rename to run.command to double-click it)
cd "$(dirname "$0")"

echo
echo "   ================================================================"
echo "      A U T O C A R E   P R O"
echo "      Smart Vehicle Maintenance System  //  SVMS"
echo "   ================================================================"
echo
echo "   How do you want to run it?"
echo
echo "      [1]  On this computer   - browser + a Wi-Fi address for your phone (default)"
echo "      [2]  Public link        - same, plus a free https link anyone can open"
echo "      [3]  Single file only   - just open AutoCare-Pro.html"
echo
read -r -t 10 -p "   Press 1, 2 or 3 then Enter [1]: " PICK
echo
PICK="${PICK:-1}"

open_file() {
  (xdg-open AutoCare-Pro.html 2>/dev/null || open AutoCare-Pro.html 2>/dev/null) \
    || echo "   Open AutoCare-Pro.html in your browser manually."
}

case "$PICK" in
  3)
    open_file
    ;;
  2)
    if command -v node >/dev/null 2>&1; then
      echo "   Starting the server and opening a public link..."
      echo "   (macOS needs cloudflared:  brew install cloudflared)"
      echo
      exec node share.js
    else
      echo "   The public link needs Node.js - install it from https://nodejs.org"
    fi
    ;;
  *)
    echo "   Starting the local server... (Ctrl+C to stop)"
    echo
    if command -v node >/dev/null 2>&1; then
      echo "   Runtime found: Node.js"
      exec node server.js
    elif command -v python3 >/dev/null 2>&1; then
      echo "   Runtime found: Python 3"
      exec python3 server.py
    else
      echo "   Neither Node.js nor Python 3 found - opening the single file."
      open_file
    fi
    ;;
esac
