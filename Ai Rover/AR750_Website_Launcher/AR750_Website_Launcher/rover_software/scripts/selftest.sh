#!/usr/bin/env bash
# The whole website, end to end, against a throwaway copy of the rover.
#
#     bash scripts/selftest.sh
#
# It starts a second, simulated rover on port 8091 with its own empty data
# folder, calls every page and presses every button on it, prints a
# pass/fail line for each, then stops it and deletes it. The real rover on
# port 8080, its database, its photos and its password are never touched.
cd "$(dirname "$0")/.." || exit 1

python3 tests/console_selftest_config.py >/dev/null || exit 1
nohup python3 -m ar750.main --config ar750/_config_selftest.yaml --port 8091 \
  </dev/null >/tmp/ar750_selftest_server.log 2>&1 &
PID=$!

# wait for it to answer rather than guessing a number of seconds
for _ in $(seq 1 40); do
  python3 -c "import socket; socket.create_connection(('127.0.0.1', 8091), 1)" \
    2>/dev/null && break
  sleep 1
done

python3 tests/console_selftest.py 8091
RC=$?

kill "$PID" 2>/dev/null
sleep 1
rm -rf data_selftest ar750/_config_selftest.yaml
exit $RC
