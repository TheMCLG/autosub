import os
import sys
import logging
from utils import str_to_bool
from flask import Flask, request, Response
import json
import requests
import xml.etree.ElementTree as ET
from tasks import start_transcription

#Config variables
PLEX_URL = os.getenv('PLEX_URL', 'http://127.0.0.1:32400') #Plex server URL including http(s):// and port
PLEX_TOKEN = os.getenv('PLEX_TOKEN', 'xxxxxxxxxxxxxx') #Your Plex token
WEBHOOK_PORT = os.getenv('WEBHOOK_PORT', 8765) #Port to listen for webhook events
DEBUG_LOGGING = str_to_bool(os.getenv('DEBUG_LOGGING', 'False')) #Set to True to enable debug logging

#Logging configuration
if DEBUG_LOGGING:
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
log = logging.getLogger('autosub')

#Debug info
log.debug(f'PLEX_URL: {PLEX_URL}')
log.debug(f'PLEX_TOKEN: {PLEX_TOKEN}')
log.debug(f'WEBHOOK_PORT: {WEBHOOK_PORT}')
log.debug(f'DEBUG_LOGGING: {DEBUG_LOGGING}')

app = Flask(__name__)
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Processes incoming Plex webhook events.

    Listens for POST requests and extracts the payload. If the event type
    is 'library.new', it logs the event and continues processing the new library item.
    Otherwise, the event type is logged and discarded.
    """
    if 'PlexMediaServer' in request.headers.get('User-Agent'):
        log.debug(request.form['payload'])
        payload = json.loads(request.form['payload'])
        event = payload['event']
        if(event == 'library.new'):
            log.info('New library item detected')
            get_metadata(payload)
        else:
            log.info(f'Discarding event type: {event}')
    else:
        log.error('Invalid User-Agent')
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
    filepath = ""
    url = f"{PLEX_URL}/library/metadata/{payload['Metadata']['ratingKey']}" #[Metadata][ratingKey] contains the ID for the new library item
    headers = {
        'X-Plex-Token': PLEX_TOKEN,
    }
    log.debug(f"Requesting metadata from {url}")
    response = requests.get(url, headers=headers) #TODO: Add error handling
    log.info('Reveived metadata response')
    log.debug(response.content)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        log.debug(ET.tostring(root))
        for part in root.iter('Part'): #Check for the 'Part' element because Plex is weird
            for att in part.attrib:
                if att == 'file':
                    filepath = part.attrib[att]
        if filepath:
            log.info(f"Filepath: {filepath}")
            audio_lang = root.find('.//Stream[2]').attrib['languageCode'] #Hardcoded to the second stream, should be primary audio in most cases
            log.info(f'Audio language: {audio_lang}')
            if audio_lang != 'eng': #TODO: Add support for multiple languages
                log.info(f'Creating task for {filepath}')
                start_transcription.delay(filepath)
            else:
                log.info('Audio language is English, skipping')
        else:
            log.debug('No file element found in metadata root, skipping')
    else:
        log.error(f'Request error: {response.status_code}')

app.run(debug=DEBUG_LOGGING, host='0.0.0.0', port=int(WEBHOOK_PORT))