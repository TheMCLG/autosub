import os
import sys
import logging
import threading
from time import perf_counter
import stable_whisper

# Config variables
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTETYPE = os.getenv("WHISPER_COMPUTETYPE", "int8")
WHISPER_CPUTHREADS = os.getenv("WHISPER_CPUTHREADS", 2)
WHISPER_TASK = os.getenv("WHISPER_TASK", "translate")

log = logging.getLogger("autosub")

# Global singleton for the model and locks for thread safety
_MODEL = None
_MODEL_INIT_LOCK = threading.Lock()
_TRANSCRIPTION_LOCK = threading.Lock()

def get_model():
    global _MODEL
    if _MODEL is None:
        with _MODEL_INIT_LOCK:
            if _MODEL is None:
                log.info(f"Loading whisper model {WHISPER_MODEL}...")
                _MODEL = stable_whisper.load_faster_whisper(
                    WHISPER_MODEL,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTETYPE,
                    cpu_threads=int(WHISPER_CPUTHREADS),
                )
                log.info("Whisper model loaded successfully.")
    return _MODEL

import tempfile
import requests

def start_transcription(rating_key, part_key, plex_url, plex_token):
    try:
        model = get_model()
        start_time = perf_counter()
        download_url = f"{plex_url}{part_key}?X-Plex-Token={plex_token}"
        log.info(f"Starting transcription for ratingKey: {rating_key}")

        # Ensure only one thread is actively transcribing on the GPU/CPU at a time
        with _TRANSCRIPTION_LOCK:
            result = model.transcribe_stable(download_url, task=WHISPER_TASK, vad=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_filepath = os.path.join(temp_dir, "aigen.en.srt")
            result.to_srt_vtt(temp_filepath, word_level=False)

            upload_url = f"{plex_url}/library/metadata/{rating_key}/subtitles"
            params = {
                "title": "autosub",
                "format": "srt",
                "X-Plex-Token": plex_token
            }
            with open(temp_filepath, 'rb') as f:
                upload_response = requests.post(upload_url, params=params, data=f, timeout=10)

            if upload_response.status_code in (200, 201):
                log.info(f"Successfully uploaded subtitle for ratingKey: {rating_key}")
            else:
                log.error(f"Failed to upload subtitle for ratingKey {rating_key}. Status code: {upload_response.status_code}")

        log.info(f"Transcription for ratingKey: {rating_key} completed in {perf_counter() - start_time} seconds")
    except Exception as e:
        log.exception(f"Error processing ratingKey {rating_key}: {e}")
