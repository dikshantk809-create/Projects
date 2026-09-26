"""Wait until the console is actually answering, then get out of the way.

Opening the browser a second after starting the server gives you an error page
and makes people think it is broken, so this holds the door until the port
answers.
"""
import socket
import sys
import time

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
deadline = time.time() + 90

sys.stdout.write("   starting")
sys.stdout.flush()
while time.time() < deadline:
    s = socket.socket()
    s.settimeout(0.6)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        print("\n   ready.")
        sys.exit(0)
    except OSError:
        pass
    finally:
        try:
            s.close()
        except OSError:
            pass
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(0.7)

print("\n   It did not start within 90 seconds.")
print("   Look at the black window titled 'AR-750 website' for the reason.")
sys.exit(1)
