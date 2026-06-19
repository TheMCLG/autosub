#!/bin/bash
PORT="${WEBHOOK_PORT:-8765}"
# Use a single sync worker. Give it an extremely high timeout and graceful timeout
# so that when the container is stopped, Gunicorn will wait for the atexit hook
# to finish any background transcriptions before sending SIGKILL.
gunicorn -w 1 -k sync --timeout 3600 --graceful-timeout 3600 -b 0.0.0.0:$PORT autosub:app
