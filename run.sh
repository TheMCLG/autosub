#!/bin/bash

celery -A tasks worker --loglevel=INFO &
python3 -u autosub.py