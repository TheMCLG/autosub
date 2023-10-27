#!/bin/bash

celery -A tasks worker --loglevel=INFO --concurrency 3 &
python3 -u autosub.py