import os
import sys
import logging
from utils import str_to_bool
from utils import str_to_list
from flask import Flask, request, Response
import json
import requests
import xml.etree.ElementTree as ET
from tasks import start_transcription

# Config variables
PLEX_URL = os.getenv("PLEX_URL", "http://127.0.0.1:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "xxxxxxxxxxxxxx")
WEBHOOK_PORT = os.getenv("WEBHOOK_PORT", 8765)
SKIP_LANGUAGES = str_to_list(os.getenv("SKIP_LANGUAGES", "en"))
SKIP_SUB_LANGUAGES = str_to_list(os.getenv("SKIP_SUB_LANGUAGES", "en"))
DEBUG_LOGGING = str_to_bool(os.getenv("DEBUG_LOGGING", "False"))

# Logging configuration
if DEBUG_LOGGING:
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
else:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("autosub")

# Debug info
log.debug(f"PLEX_URL: {PLEX_URL}")
log.debug(f"PLEX_TOKEN: {PLEX_TOKEN}")
log.debug(f"WEBHOOK_PORT: {WEBHOOK_PORT}")
log.debug(f"SKIP_LANGUAGES: {SKIP_LANGUAGES}")
log.debug(f"SKIP_SUB_LANGUAGES: {SKIP_SUB_LANGUAGES}")
log.debug(f"DEBUG_LOGGING: {DEBUG_LOGGING}")

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Processes incoming Plex webhook events.

    Listens for POST requests and extracts the payload. If the event type
    is 'library.new', it logs the event and continues processing the new library item.
    Otherwise, the event type is logged and discarded.
    """
    if "PlexMediaServer" in request.headers.get("User-Agent"):
        log.debug(request.form["payload"])
        payload = json.loads(request.form["payload"])
        event = payload["event"]
        if event == "library.new":
            log.info("New library item detected")
            get_metadata(payload)
        else:
            log.info(f"Discarding event type: {event}")
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
        filepath = parse_plex_xml(response.content, SKIP_LANGUAGES, SKIP_SUB_LANGUAGES)
        if filepath:
            log.info(f"Creating task for {filepath}")
            start_transcription.delay(filepath)
    else:
        log.error(f"Request error: {response.status_code}")


def parse_plex_xml(response, skip_languages, skip_sub_languages):
    root = ET.fromstring(response)
    filepath = ""

    # Check if the Plex metadata contains a filepath
    for part in root.iter("Part"):
        for att in part.attrib:
            if att == "file":
                filepath = part.attrib[att]
                log.info(f"Filepath is {filepath}")

    if filepath:
        # Check for audio streams and return False if they match one of the audio languages we want to skip
        for stream in root.iter("Stream"):
            for att in stream.attrib:
                if att == "channels":
                    log.info(f"Found an audio stream")
                    if skip_languages:
                        for language in skip_languages:
                            if (
                                stream.attrib["languageTag"] == language
                                or stream.attrib["languageCode"] == language
                            ):
                                log.info(f"Audio language is {language}, skipping")
                                return False
                            else:
                                log.info(
                                    f"Audio language is not {language}, continuing"
                                )

        # Check for subtitles and return False if they match one of the sub languages we want to skip
        for stream in root.iter("Stream"):
            for att in stream.attrib:
                if att == "codec":
                    if stream.attrib["codec"] == "srt":
                        log.info(f"Found a subtitle stream")
                        if skip_sub_languages:
                            for sublang in skip_sub_languages:
                                if (
                                    stream.attrib["languageTag"] == sublang
                                    or stream.attrib["languageCode"] == sublang
                                ):
                                    log.info(
                                        f"Subtitle language is {sublang}, skipping"
                                    )
                                    return False
                                else:
                                    log.info(
                                        f"Subtitle language is not {sublang}, continuing"
                                    )

        return filepath
    else:
        log.info("No filepath found, skipping")
        return False


app.run(debug=DEBUG_LOGGING, host="0.0.0.0", port=int(WEBHOOK_PORT))
