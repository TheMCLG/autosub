import os
import sys
import logging
from utils import str_to_bool
from time import perf_counter
from celery import Celery
import stable_whisper

#Config variables
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'medium') #tiny, base, small, medium, large
WHISPER_DEVICE = os.getenv('WHISPER_DEVICE', 'cpu') #cpu or cuda for Nvidia GPU's
WHISPER_COMPUTETYPE = os.getenv('WHISPER_COMPUTETYPE', 'int8') #Recommended: int8 for cpu or float16 for cuda
WHISPER_CPUTHREADS = os.getenv('WHISPER_CPUTHREADS', 2) #Number of CPU threads to use (only applicable for cpu)
DEBUG_LOGGING = str_to_bool(os.getenv('DEBUG_LOGGING', 'False')) #Set to True to enable debug logging

#Logging configuration
if DEBUG_LOGGING:
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
log = logging.getLogger('autosub')

#Debug info
log.debug(f'WHISPER_MODEL: {WHISPER_MODEL}')
log.debug(f'WHISPER_DEVICE: {WHISPER_DEVICE}')
log.debug(f'WHISPER_COMPUTETYPE: {WHISPER_COMPUTETYPE}')
log.debug(f'WHISPER_CPUTHREADS: {WHISPER_CPUTHREADS}')

app = Celery('tasks', broker='redis://redis')

@app.task
def start_transcription(filepath):
    """
    Transcribe and translate the audio of a given video file and save the transcription to an SRT format.
    Note: The current implementation assumes that the file path matches relative to the Plex server.
    """
    model = stable_whisper.load_faster_whisper(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTETYPE, cpu_threads=int(WHISPER_CPUTHREADS))
    try:
        start_time = perf_counter()
        log.info(f'Starting transcription for {filepath}')
        result = model.transcribe_stable(filepath, task='translate')
        result.to_srt_vtt(filepath.rsplit('.', 1)[0] + '.aigen.en.srt', word_level=False)
        elapsed_time = perf_counter() - start_time
        log.info(f'Transcription for {filepath} completed in {elapsed_time} seconds')
    except Exception as e:
        log.error(f'Error processing {filepath}: {e}')