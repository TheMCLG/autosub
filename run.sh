#!/bin/bash
PORT="${WEBHOOK_PORT:-8765}"
gunicorn -w 1 -k gthread --threads 1 -b 0.0.0.0:$PORT autosub:app
