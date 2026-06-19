import unittest
from utils import str_to_bool, str_to_list

import json
from unittest.mock import patch, MagicMock
from autosub import app, parse_plex_xml, get_metadata

class TestUtils(unittest.TestCase):
    def test_str_to_bool(self):
        self.assertTrue(str_to_bool("True"))
        self.assertTrue(str_to_bool("true"))
        self.assertFalse(str_to_bool("False"))
        self.assertFalse(str_to_bool("false"))
        self.assertIsNone(str_to_bool("Invalid"))

    def test_str_to_list(self):
        self.assertIsNone(str_to_list("None"))
        self.assertEqual(str_to_list("en, fr"), ["en", "fr"])
        self.assertEqual(str_to_list("en,fr"), ["en", "fr"])
        self.assertEqual(str_to_list("en"), ["en"])

class TestAutosub(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    @patch('autosub.get_metadata')
    def test_webhook_library_new(self, mock_get_metadata):
        payload = {"event": "library.new", "Metadata": {"ratingKey": "123"}}
        response = self.client.post(
            "/webhook",
            data={"payload": json.dumps(payload)},
            headers={"User-Agent": "PlexMediaServer"}
        )
        self.assertEqual(response.status_code, 200)
        mock_get_metadata.assert_called_once_with(payload)

    @patch('autosub.get_metadata')
    def test_webhook_other_event(self, mock_get_metadata):
        payload = {"event": "media.play"}
        response = self.client.post(
            "/webhook",
            data={"payload": json.dumps(payload)},
            headers={"User-Agent": "PlexMediaServer"}
        )
        self.assertEqual(response.status_code, 200)
        mock_get_metadata.assert_not_called()

    def test_webhook_invalid_user_agent(self):
        response = self.client.post("/webhook", data={"payload": "{}"})
        self.assertEqual(response.status_code, 200)

    def test_parse_plex_xml_no_filepath(self):
        xml = '<MediaContainer><Video></Video></MediaContainer>'
        self.assertFalse(parse_plex_xml(xml, ["en"], ["en"]))

    def test_parse_plex_xml_valid_file_and_no_skip(self):
        xml = '''<MediaContainer>
                    <Video>
                        <Media>
                            <Part file="/path/to/video.mp4">
                                <Stream streamType="2" languageCode="fr" />
                            </Part>
                        </Media>
                    </Video>
                 </MediaContainer>'''
        self.assertEqual(parse_plex_xml(xml, ["en"], ["en"]), "/path/to/video.mp4")

    def test_parse_plex_xml_skip_audio_lang(self):
        xml = '''<MediaContainer>
                    <Video>
                        <Media>
                            <Part file="/path/to/video.mp4">
                                <Stream streamType="2" languageCode="en" channels="2" />
                            </Part>
                        </Media>
                    </Video>
                 </MediaContainer>'''
        self.assertFalse(parse_plex_xml(xml, ["en"], ["en"]))

    def test_parse_plex_xml_skip_sub_lang(self):
        xml = '''<MediaContainer>
                    <Video>
                        <Media>
                            <Part file="/path/to/video.mp4">
                                <Stream streamType="3" codec="srt" languageCode="en" />
                            </Part>
                        </Media>
                    </Video>
                 </MediaContainer>'''
        self.assertFalse(parse_plex_xml(xml, ["en"], ["en"]))

    @patch('autosub.requests.get')
    @patch('autosub.start_transcription.delay')
    def test_get_metadata(self, mock_delay, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = '''<MediaContainer>
                    <Video>
                        <Media>
                            <Part file="/path/to/video.mp4">
                                <Stream streamType="2" languageCode="fr" />
                            </Part>
                        </Media>
                    </Video>
                 </MediaContainer>'''
        mock_get.return_value = mock_response

        get_metadata({"Metadata": {"ratingKey": "123"}})

        mock_delay.assert_called_once_with("/path/to/video.mp4")

    @patch('autosub.requests.get')
    @patch('autosub.start_transcription.delay')
    def test_get_metadata_error_status(self, mock_delay, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        get_metadata({"Metadata": {"ratingKey": "123"}})
        mock_delay.assert_not_called()


class TestTasks(unittest.TestCase):
    @patch('tasks.stable_whisper')
    @patch('tasks.perf_counter')
    def test_start_transcription(self, mock_perf_counter, mock_stable_whisper):
        from tasks import start_transcription
        mock_perf_counter.side_effect = [0.0, 1.5]

        mock_model = MagicMock()
        mock_stable_whisper.load_faster_whisper.return_value = mock_model

        mock_result = MagicMock()
        mock_model.transcribe_stable.return_value = mock_result

        start_transcription("/path/to/movie.mkv")

        mock_stable_whisper.load_faster_whisper.assert_called_once()
        mock_model.transcribe_stable.assert_called_once_with("/path/to/movie.mkv", task="translate", vad=True)
        mock_result.to_srt_vtt.assert_called_once_with("/path/to/movie.aigen.en.srt", word_level=False)

    @patch('tasks.stable_whisper')
    def test_start_transcription_exception(self, mock_stable_whisper):
        from tasks import start_transcription
        mock_model = MagicMock()
        mock_stable_whisper.load_faster_whisper.return_value = mock_model
        mock_model.transcribe_stable.side_effect = Exception("Transcription error")

        # Test that it gracefully catches the exception without crashing
        start_transcription("/path/to/movie.mkv")

if __name__ == '__main__':
    unittest.main()
