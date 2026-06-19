import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from flask import Flask, request, Response
import json
import requests
import xml.etree.ElementTree as ET
import stable_whisper

def str_to_bool(s):
    return s.lower() in ["true", "1", "yes"] if isinstance(s, str) else bool(s)

# Config variables
PLEX_URL = os.getenv("PLEX_URL", "http://127.0.0.1:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "xxxxxxxxxxxxxx")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 8765))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTETYPE = os.getenv("WHISPER_COMPUTETYPE", "int8")
WHISPER_CPUTHREADS = int(os.getenv("WHISPER_CPUTHREADS", 2))
DEBUG_LOGGING = str_to_bool(os.getenv("DEBUG_LOGGING", "False"))

# Logging configuration
logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG if DEBUG_LOGGING else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("autosub")

# Debug info
log.debug(f"PLEX_URL: {PLEX_URL}")
log.debug(f"WEBHOOK_PORT: {WEBHOOK_PORT}")
log.debug(f"WHISPER_MODEL: {WHISPER_MODEL}")
log.debug(f"WHISPER_DEVICE: {WHISPER_DEVICE}")
log.debug(f"WHISPER_COMPUTETYPE: {WHISPER_COMPUTETYPE}")

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=1)


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Processes incoming Plex webhook events.

    Listens for POST requests and extracts the payload. If the event type
    is 'library.new', it logs the event and continues processing the new library item.
    Otherwise, the event type is logged and discarded.
    """
    if "PlexMediaServer" in request.headers.get("User-Agent", ""):
        try:
            log.debug(request.form["payload"])
            payload = json.loads(request.form["payload"])
            event = payload["event"]
            if event == "library.new":
                log.info("New library item detected")
                get_metadata(payload)
            else:
                log.info(f"Discarding event type: {event}")
        except Exception as e:
            log.error(f"Error parsing webhook payload: {e}")
    else:
        log.error("Invalid User-Agent")
    return Response(status=200)


def get_metadata(payload):
    """
    Fetch metadata for a given payload from Plex.

    This function queries the Plex server to retrieve the full file path and
    audio language for the library item in the payload. If the primary audio
    language of the file is not English, it initiates a transcription task
    for that file.

    Note: PLEX_URL and PLEX_TOKEN need to be set appropriately before making a request.
    """
    url = f"{PLEX_URL}/library/metadata/{payload['Metadata']['ratingKey']}"  # [Metadata][ratingKey] contains the ID for the new library item
    headers = {
        "X-Plex-Token": PLEX_TOKEN,
    }
    log.debug(f"Requesting metadata from {url}")
    response = requests.get(url, headers=headers)  # TODO: Add error handling
    log.info("Reveived metadata response")
    log.debug(response.content)
    if response.status_code == 200:
        filepath = parse_plex_xml(response.content)
        if filepath:
            log.info(f"Creating task for {filepath}")
            executor.submit(start_transcription, filepath)
    else:
        log.error(f"Request error: {response.status_code}")


def start_transcription(filepath):
    """
    Transcribe and translate the audio of a given video file and save the transcription to an SRT format.
    """
    model = stable_whisper.load_faster_whisper(
        WHISPER_MODEL,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTETYPE,
        cpu_threads=WHISPER_CPUTHREADS,
    )
    try:
        start_time = perf_counter()
        log.info(f"Starting transcription for {filepath}")
        result = model.transcribe_stable(filepath, task="translate", vad=True)
        result.to_srt_vtt(
            filepath.rsplit(".", 1)[0] + ".aigen.en.srt", word_level=False
        )
        elapsed_time = perf_counter() - start_time
        log.info(f"Transcription for {filepath} completed in {elapsed_time} seconds")
    except Exception as e:
        log.error(f"Error processing {filepath}: {e}")

def parse_plex_xml(response):
    root = ET.fromstring(response)
    filepath = ""

    # Check if the Plex metadata contains a filepath
    for part in root.iter("Part"):
        if "file" in part.attrib:
            filepath = part.attrib["file"]
            log.info(f"Filepath is {filepath}")
            break

    if filepath:
        # Look for Dutch audio streams
        for stream in root.iter("Stream"):
            if "channels" in stream.attrib:  # Indicates an audio stream
                lang_tag = stream.attrib.get("languageTag", "").lower()
                lang_code = stream.attrib.get("languageCode", "").lower()
                if lang_tag in ["nl", "nld", "dut"] or lang_code in ["nl", "nld", "dut"]:
                    log.info(f"Found Dutch audio stream. Proceeding with subtitle generation for {filepath}.")
                    return filepath

        log.info(f"No Dutch audio stream found in {filepath}, skipping.")
        return False
    else:
        log.info("No filepath found, skipping.")
        return False


app.run(debug=DEBUG_LOGGING, host="0.0.0.0", port=int(WEBHOOK_PORT))
