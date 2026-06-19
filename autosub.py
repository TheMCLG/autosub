import os
import sys
import logging
from flask import Flask, request, Response
import json
import requests
import xml.etree.ElementTree as ET
import concurrent.futures
import signal
from tasks import start_transcription

def str_to_bool(s):
    return str(s).lower() in ("true", "1")

def str_to_list(s):
    if not s or s == "None": return None
    return [x.strip() for x in s.split(',')]

# Config variables
PLEX_URL = os.getenv("PLEX_URL", "http://127.0.0.1:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "xxxxxxxxxxxxxx")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 8765))
SKIP_LANGUAGES = str_to_list(os.getenv("SKIP_LANGUAGES", "en"))
SKIP_SUB_LANGUAGES = str_to_list(os.getenv("SKIP_SUB_LANGUAGES", "en"))
DEBUG_LOGGING = str_to_bool(os.getenv("DEBUG_LOGGING", "False"))
MAX_WORKERS = int(os.getenv("WEBHOOK_EXECUTOR_MAX_WORKERS", 1))

# Logging configuration
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG if DEBUG_LOGGING else logging.INFO)
log = logging.getLogger("autosub")

# Thread pool for background tasks - 1 worker is ideal as transcription is heavily CPU/GPU bound
executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Graceful shutdown handler
def graceful_shutdown(signum, frame):
    log.info("Received shutdown signal. Waiting for active transcriptions to finish...")
    executor.shutdown(wait=True)
    log.info("Shutdown complete.")
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    if "PlexMediaServer" in request.headers.get("User-Agent", ""):
        try:
            payload_str = request.form.get("payload", "{}")
            if not payload_str:
                payload_str = "{}"
            payload = json.loads(payload_str)
            if payload.get("event") == "library.new":
                log.info("New library item detected")
                get_metadata(payload)
            else:
                log.info(f"Discarding event type: {payload.get('event')}")
        except json.JSONDecodeError:
            log.exception(f"Invalid JSON payload snippet: {request.form.get('payload', '')[:200]}")
    else:
        log.error("Invalid User-Agent")
    return Response(status=200)

def get_metadata(payload):
    try:
        # Validate ratingKey exists and is string or int
        rating_key = payload.get("Metadata", {}).get("ratingKey")
        if not rating_key:
            log.error("No ratingKey found in payload")
            return

        url = f"{PLEX_URL}/library/metadata/{rating_key}"
        headers = {"X-Plex-Token": PLEX_TOKEN}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            filepath = parse_plex_xml(response.content, SKIP_LANGUAGES, SKIP_SUB_LANGUAGES)
            if filepath is not None:
                log.info(f"Creating task for {filepath}")
                executor.submit(start_transcription, filepath)
        else:
            log.error(f"Request error: {response.status_code}")
    except requests.RequestException as e:
        log.exception(f"Network error fetching metadata: {e}")
    except Exception as e:
        log.exception(f"Error fetching metadata: {e}")

def parse_plex_xml(response, skip_languages, skip_sub_languages):
    """
    Parses XML metadata from Plex to determine the file path and streams.
    Returns the file path string if valid, or None if skipped or missing.
    """
    try:
        root = ET.fromstring(response)
        filepath = None
        for part in root.iter("Part"):
            if "file" in part.attrib:
                filepath = part.attrib["file"]
                break

        if not filepath:
            return None

        for stream in root.iter("Stream"):
            if stream.attrib.get("streamType") == "2" or stream.attrib.get("channels"):
                lang_tag = stream.attrib.get("languageTag")
                lang_code = stream.attrib.get("languageCode")
                if skip_languages and any(l in (lang_tag, lang_code) for l in skip_languages):
                    return None
            elif stream.attrib.get("codec") == "srt":
                lang_tag = stream.attrib.get("languageTag")
                lang_code = stream.attrib.get("languageCode")
                if skip_sub_languages and any(l in (lang_tag, lang_code) for l in skip_sub_languages):
                    return None

        return filepath
    except Exception as e:
        log.exception(f"Error parsing XML from Plex: {e}")
        return None

if __name__ == "__main__":
    app.run(debug=DEBUG_LOGGING, host="0.0.0.0", port=WEBHOOK_PORT)
