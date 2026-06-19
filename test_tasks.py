import unittest
from unittest.mock import patch, MagicMock
import os
import tasks

class TestTasks(unittest.TestCase):

    @patch('tasks.stable_whisper.load_faster_whisper')
    def test_start_transcription_success(self, mock_load_faster_whisper):
        mock_model = MagicMock()
        mock_result = MagicMock()
        mock_model.transcribe_stable.return_value = mock_result
        mock_load_faster_whisper.return_value = mock_model

        filepath = "/path/to/video.mp4"
        tasks.start_transcription(filepath)

        # Assert model is loaded with correct params
        mock_load_faster_whisper.assert_called_once_with(
            tasks.WHISPER_MODEL,
            device=tasks.WHISPER_DEVICE,
            compute_type=tasks.WHISPER_COMPUTETYPE,
            cpu_threads=int(tasks.WHISPER_CPUTHREADS)
        )

        # Assert transcribe was called
        mock_model.transcribe_stable.assert_called_once_with(filepath, task=tasks.WHISPER_TASK, vad=True)

        # Assert to_srt_vtt was called to save SRT file
        mock_result.to_srt_vtt.assert_called_once_with("/path/to/video.aigen.en.srt", word_level=False)

    @patch('tasks.stable_whisper.load_faster_whisper')
    @patch('tasks.log.error')
    def test_start_transcription_exception(self, mock_log_error, mock_load_faster_whisper):
        mock_model = MagicMock()
        mock_model.transcribe_stable.side_effect = Exception("Transcription failed")
        mock_load_faster_whisper.return_value = mock_model

        filepath = "/path/to/video.mp4"
        tasks.start_transcription(filepath)

        # Exception should be caught and logged
        mock_log_error.assert_called_once()
        self.assertIn("Error processing /path/to/video.mp4", mock_log_error.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
