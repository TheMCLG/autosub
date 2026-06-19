import unittest
from unittest.mock import patch, MagicMock
import json
import os

# Set environment variables for testing before importing autosub
os.environ["PLEX_URL"] = "http://localhost:32400"
os.environ["PLEX_TOKEN"] = "testtoken"

import autosub

class TestAutosub(unittest.TestCase):
    def setUp(self):
        self.app = autosub.app.test_client()
        self.app.testing = True

    def test_webhook_invalid_user_agent(self):
        response = self.app.post('/webhook', headers={'User-Agent': 'OtherAgent'}, data={'payload': '{}'})
        self.assertEqual(response.status_code, 200)

    @patch('autosub.get_metadata')
    def test_webhook_library_new(self, mock_get_metadata):
        payload = {'event': 'library.new'}
        response = self.app.post('/webhook',
                                 headers={'User-Agent': 'PlexMediaServer'},
                                 data={'payload': json.dumps(payload)})
        self.assertEqual(response.status_code, 200)
        mock_get_metadata.assert_called_once_with(payload)

    @patch('autosub.get_metadata')
    def test_webhook_other_event(self, mock_get_metadata):
        payload = {'event': 'media.play'}
        response = self.app.post('/webhook',
                                 headers={'User-Agent': 'PlexMediaServer'},
                                 data={'payload': json.dumps(payload)})
        self.assertEqual(response.status_code, 200)
        mock_get_metadata.assert_not_called()

    @patch('autosub.start_transcription.delay')
    @patch('autosub.parse_plex_xml')
    @patch('autosub.requests.get')
    def test_get_metadata_success(self, mock_requests_get, mock_parse_plex_xml, mock_start_transcription):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<xml></xml>'
        mock_requests_get.return_value = mock_response

        mock_parse_plex_xml.return_value = '/path/to/media.mp4'

        payload = {'Metadata': {'ratingKey': '1234'}}
        autosub.get_metadata(payload)

        mock_requests_get.assert_called_once_with('http://localhost:32400/library/metadata/1234', headers={'X-Plex-Token': 'testtoken'})
        mock_parse_plex_xml.assert_called_once_with(b'<xml></xml>', autosub.SKIP_LANGUAGES, autosub.SKIP_SUB_LANGUAGES)
        mock_start_transcription.assert_called_once_with('/path/to/media.mp4')

    @patch('autosub.start_transcription.delay')
    @patch('autosub.parse_plex_xml')
    @patch('autosub.requests.get')
    def test_get_metadata_no_filepath(self, mock_requests_get, mock_parse_plex_xml, mock_start_transcription):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<xml></xml>'
        mock_requests_get.return_value = mock_response

        mock_parse_plex_xml.return_value = False

        payload = {'Metadata': {'ratingKey': '1234'}}
        autosub.get_metadata(payload)

        mock_start_transcription.assert_not_called()

    @patch('autosub.start_transcription.delay')
    @patch('autosub.requests.get')
    @patch('autosub.log.error')
    def test_get_metadata_request_error(self, mock_log_error, mock_requests_get, mock_start_transcription):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests_get.return_value = mock_response

        payload = {'Metadata': {'ratingKey': '1234'}}
        autosub.get_metadata(payload)

        mock_start_transcription.assert_not_called()
        mock_log_error.assert_called_once()

    def test_parse_plex_xml_skip_audio_lang(self):
        xml_data = '''
        <MediaContainer>
            <Part file="/path/to/media.mp4" />
            <Stream streamType="2" channels="2" languageTag="de" languageCode="de" />
        </MediaContainer>
        '''
        result = autosub.parse_plex_xml(xml_data, ['de'], [])
        self.assertFalse(result)

    def test_parse_plex_xml_skip_sub_lang(self):
        xml_data = '''
        <MediaContainer>
            <Part file="/path/to/media.mp4" />
            <Stream streamType="2" channels="2" languageTag="es" languageCode="es" />
            <Stream codec="srt" languageTag="en" languageCode="en" />
        </MediaContainer>
        '''
        result = autosub.parse_plex_xml(xml_data, ['de'], ['en'])
        self.assertFalse(result)

    def test_parse_plex_xml_success(self):
        xml_data = '''
        <MediaContainer>
            <Part file="/path/to/media.mp4" />
            <Stream streamType="2" channels="2" languageTag="es" languageCode="es" />
        </MediaContainer>
        '''
        result = autosub.parse_plex_xml(xml_data, ['en'], ['en'])
        self.assertEqual(result, '/path/to/media.mp4')

    def test_parse_plex_xml_no_filepath(self):
        xml_data = '''
        <MediaContainer>
            <Part />
        </MediaContainer>
        '''
        result = autosub.parse_plex_xml(xml_data, ['en'], ['en'])
        self.assertFalse(result)

    def test_parse_plex_xml_missing_language_attributes(self):
        xml_data = '''
        <MediaContainer>
            <Part file="/path/to/media.mp4" />
            <Stream streamType="2" channels="2" />
        </MediaContainer>
        '''
        # Should not throw KeyError, and should proceed normally returning the filepath
        result = autosub.parse_plex_xml(xml_data, ['en'], ['en'])
        self.assertEqual(result, '/path/to/media.mp4')


if __name__ == '__main__':
    unittest.main()
