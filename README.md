# AutoSub - AI Generated Subtitles For Plex
AutoSub is a Python application that listens to Plex webhook events for newly added media. When it receives a new media event, it retrieves metadata from Plex to determine the language of the primary audio stream. If this audio stream is not in English, it then uses the [stable-ts](https://github.com/jianfch/stable-ts) library to transcribe and generate English subtitles.

Inspired by [McCloudS](https://github.com/McCloudS) / [subgen](https://github.com/McCloudS/subgen/tree/d3c0aa2b5b62ae08900dde5ce05dd30a4e806722) 

---
## Features
- Automatically scans new Plex media for audio that is not English.
- Basic multithreading using [celery](https://github.com/celery/celery).
- Supports CPU or Nvidia GPU's for transcribing.
- Uses [stable-ts](https://github.com/jianfch/stable-ts) and [faster-whisper](https://github.com/guillaumekln/faster-whisper) for efficient audio transcription and translation to English.
- Saves the transcription to an SRT file in the media's directory for use as subtitles.

## Prerequisites & Limitations
> [!IMPORTANT]
> Make sure your media file paths are setup correctly.
- Requires media folder paths to match relative to the Plex server.
If your Plex media path is `/media/movies/video.mp4`, then autosub needs to be able to reach that media using the same path.
- Only translates into English subtitles.
- Currently skips any media that contains English audio.

## Setup & Configuration

### Manual
> [!IMPORTANT]
> GPU execution requires these NVIDIA libraries to be installed: cuBLAS for CUDA 11 & cuDNN 8 for CUDA 11
> [Read More](https://github.com/guillaumekln/faster-whisper#gpu)
1. Install Python3, python3-pip, and ffmpeg.
2. Install dependencies: `pip install flask stable-ts faster-whisper requests "celery[redis]" `
3. Clone this repository: `git clone https://github.com/TheMCLG/autosub.git`
4. Configure the Global Variables in `autosub.py` and `tasks.py` - see the Config Variables table below.
5. Run `run.sh` or start both scripts manually by running:
   - `celery -A tasks worker --loglevel=INFO &`
   - `python3 -u autosub.py`

### Docker
The Dockerfile can be found in this repo, alongside an example `docker-compose.yml`.
A prebuilt image can be downloaded from: [themclg/autosub:latest](https://hub.docker.com/layers/themclg/autosub/latest/images/sha256-7595f100b774b3835ad02d05df27992b6bc70fbf10927c835e1d2a17907a05d4?context=repo)

### Plex 
**Webhook**

Plex Webhooks are configured under Account settings in Plex Web App (the Account item under the top right user menu).
Add a new Webhook for your autosub address.
> [!NOTE]
> If you are not receiving `library.new` webhook events, make sure push notifications are turned on for your Plex Server (don't ask me why).

**Plex Token**

You need to add your Plex authentication token to the config variables in order for autosub to work.
Finding your token is pretty simple:
1. Sign in to your Plex account in Plex Web App.
2. Browse to a library item and view the XML for it.
3. Look in the URL and find the token as the X-Plex-Token value.
 
[More info](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)


### Config Variables
| Variable           | Default                    | Description                                                |
|--------------------|----------------------------|------------------------------------------------------------|
| `PLEX_URL`         | `http://127.0.0.1:32400`    | Plex server URL including `http(s)://` and port.           |
| `PLEX_TOKEN`       | (None)                     | Your Plex token. Must be provided.                         |
| `WEBHOOK_PORT`     | `8765`                     | Port for the Flask server to listen for webhooks.         |
| `WHISPER_MODEL`    | `medium`                   | Whisper model size. Options: `tiny`, `base`, `small`, `medium`, `large`. |
| `WHISPER_DEVICE`   | `cpu`                      | Compute device for Whisper. Options: `cpu` or `cuda` for Nvidia GPU's. Note: using `cuda` requires cuBLAS and cuDNN 8 for CUDA 11 installed. |
| `WHISPER_COMPUTETYPE` | `int8`                   | Recommended: `int8` for CPU or `float16` for CUDA.         |
| `WHISPER_CPUTHREADS` | `2`                       | Number of CPU threads to use (only applicable for CPU).   |
| `DEBUG_LOGGING`    | `False`                    | Set to `True` to enable debug logging.                     |


## Future Improvements
- [ ] Add configurable option for which languages to transcribe.
- [ ] Improve audio stream detection/selection.
- [ ] Add scheduled Plex library scanning.
- [ ] Add [homepage](https://github.com/gethomepage/homepage) integration.
- [ ] General clean-up.

## Supported Audio Languages
Afrikaans, Arabic, Armenian, Azerbaijani, Belarusian, Bosnian, Bulgarian, Catalan, Chinese, Croatian, Czech, Danish, Dutch, English, Estonian, Finnish, French, Galician, German, Greek, Hebrew, Hindi, Hungarian, Icelandic, Indonesian, Italian, Japanese, Kannada, Kazakh, Korean, Latvian, Lithuanian, Macedonian, Malay, Marathi, Maori, Nepali, Norwegian, Persian, Polish, Portuguese, Romanian, Russian, Serbian, Slovak, Slovenian, Spanish, Swahili, Swedish, Tagalog, Tamil, Thai, Turkish, Ukrainian, Urdu, Vietnamese, and Welsh.

Source: [OpenAI Whisper Docs](https://platform.openai.com/docs/guides/speech-to-text/supported-languages)

## Maintenance
If and when I feel like it. This is a hobby project build mostly for my personal use.

## Credits
- [subgen](https://github.com/McCloudS/subgen/tree/d3c0aa2b5b62ae08900dde5ce05dd30a4e806722)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [stable-ts](https://github.com/jianfch/stable-ts)
- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [celery](https://github.com/celery/celery)
