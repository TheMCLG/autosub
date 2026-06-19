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

def start_transcription(filepath):
    try:
        model = get_model()
        start_time = perf_counter()
        log.info(f"Starting transcription for {filepath}")

        # Ensure only one thread is actively transcribing on the GPU/CPU at a time
        with _TRANSCRIPTION_LOCK:
            result = model.transcribe_stable(filepath, task=WHISPER_TASK, vad=True)

        result.to_srt_vtt(filepath.rsplit(".", 1)[0] + ".aigen.en.srt", word_level=False)
        log.info(f"Transcription for {filepath} completed in {perf_counter() - start_time} seconds")
    except Exception as e:
        log.exception(f"Error processing {filepath}: {e}")
