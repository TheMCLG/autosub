import unittest
from unittest.mock import patch, MagicMock
import os
import tasks

class TestTasks(unittest.TestCase):
    def setUp(self):
        # Reset the singleton before each test
        tasks._MODEL = None

    @patch('tasks.requests.post')
    @patch('tasks.tempfile.TemporaryDirectory')
    @patch('tasks.stable_whisper.load_faster_whisper')
    def test_start_transcription_success(self, mock_load_faster_whisper, mock_tempdir, mock_requests_post):
        mock_model = MagicMock()
        mock_result = MagicMock()
        mock_model.transcribe_stable.return_value = mock_result
        mock_load_faster_whisper.return_value = mock_model

        mock_temp_dir_instance = MagicMock()
        mock_tempdir.return_value.__enter__.return_value = '/tmp/mockdir'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests_post.return_value = mock_response

        # Mock open so we don't actually try to open a file when requests.post is called
        with patch('builtins.open', unittest.mock.mock_open(read_data=b'data')) as mock_file:
            tasks.start_transcription('123', '/part_key', 'http://plex:32400', 'token123')

        # Assert model is loaded with correct params
        mock_load_faster_whisper.assert_called_once_with(
            tasks.WHISPER_MODEL,
            device=tasks.WHISPER_DEVICE,
            compute_type=tasks.WHISPER_COMPUTETYPE,
            cpu_threads=int(tasks.WHISPER_CPUTHREADS)
        )

        # Assert transcribe was called with download url
        download_url = "http://plex:32400/part_key?X-Plex-Token=token123"
        mock_model.transcribe_stable.assert_called_once_with(download_url, task=tasks.WHISPER_TASK, vad=True)

        # Assert to_srt_vtt was called to save SRT file in temp dir
        mock_result.to_srt_vtt.assert_called_once_with("/tmp/mockdir/aigen.en.srt", word_level=False)

        upload_url = "http://plex:32400/library/metadata/123/subtitles"
        params = {
            "title": "autosub",
            "format": "srt",
            "X-Plex-Token": "token123"
        }
        headers = {'Accept': 'text/plain, */*'}
        mock_requests_post.assert_called_once()
        self.assertEqual(mock_requests_post.call_args[0][0], upload_url)
        self.assertEqual(mock_requests_post.call_args[1]['params'], params)
        self.assertEqual(mock_requests_post.call_args[1]['headers'], headers)


    @patch('tasks.stable_whisper.load_faster_whisper')
    @patch('tasks.log.exception')
    def test_start_transcription_exception(self, mock_log_exception, mock_load_faster_whisper):
        mock_model = MagicMock()
        mock_model.transcribe_stable.side_effect = Exception("Transcription failed")
        mock_load_faster_whisper.return_value = mock_model

        tasks.start_transcription('123', '/part_key', 'http://plex:32400', 'token123')

        # Exception should be caught and logged
        mock_log_exception.assert_called_once()
        self.assertIn("Error processing ratingKey 123", mock_log_exception.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
