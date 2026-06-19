# AutoSub - AI Generated Subtitles For Plex

[![Tests](https://github.com/TheMCLG/autosub/actions/workflows/test.yml/badge.svg)](https://github.com/TheMCLG/autosub/actions/workflows/test.yml)

AutoSub is a Python script that listens to Plex webhook events for newly added media. When it receives a new media event, it retrieves metadata from Plex to determine the language of the primary audio stream. If this audio stream is not in English, it then uses the [stable-ts](https://github.com/jianfch/stable-ts) library to transcribe and generate English subtitles.

Inspired by [McCloudS](https://github.com/McCloudS) / [subgen](https://github.com/McCloudS/subgen/tree/d3c0aa2b5b62ae08900dde5ce05dd30a4e806722) 

---
## Features
- Automatically scans new Plex media for audio that is not English.
- **Zero file system dependencies:** Operates entirely over the network via the Plex API—no volume mounts or file system access needed, simplifying containerized setups and enabling true network-only deployments.
- Supports CPU or Nvidia GPU's for transcribing.
- Uses [stable-ts](https://github.com/jianfch/stable-ts) and [faster-whisper](https://github.com/guillaumekln/faster-whisper) for efficient audio transcription and translation to English.
- Uploads the transcription directly to the Plex server as an SRT subtitle track.

## Limitations
- Faster-Whisper only supports translating text into English.
- By default, skips media containing English audio/subtitles. This is a configurable behavior.

## Setup

### Manual
> [!IMPORTANT]
> GPU execution requires these NVIDIA libraries to be installed: cuBLAS for CUDA 12 & cuDNN 8 for CUDA 12
> [Read More](https://github.com/guillaumekln/faster-whisper#gpu)
1. Install Python3, python3-pip, and ffmpeg.
2. Install dependencies: `pip install -r requirements.txt`
3. Clone this repository: `git clone https://github.com/TheMCLG/autosub.git`
4. Configure the Global Variables in `autosub.py` and `tasks.py` - see the [Variables](#Variables) table below.
5. Run `run.sh` or start the script manually by running:
   - `python3 -u autosub.py` (For production workloads it is highly recommended to run using the included `run.sh` script which leverages Gunicorn with a single worker process `-w 1` to prevent loading duplicate models into GPU memory)

### Docker
The Dockerfile can be found in this repo.
A prebuilt image can be downloaded from: [themclg/autosub:latest](https://hub.docker.com/layers/themclg/autosub/latest/images/sha256-7595f100b774b3835ad02d05df27992b6bc70fbf10927c835e1d2a17907a05d4?context=repo). The image has built-in support for cuda/GPU transcribing but you will need to map your GPU in your `docker-compose.yml`.

Example `docker-compose.yml` (Note: See the `docker-compose.yml` file in this repository for the authoritative, most up-to-date version):
```yaml
version: '3.3'
services:
  autosub:
    container_name: autosub
    image: themclg/autosub:latest
    hostname: autosub
    ports:
      - 8765:8765
    environment:
      - "PLEX_URL=http://127.0.0.1:32400" #Plex server URL including http(s):// and port
      - "PLEX_TOKEN=xxxxxxxxxxxxxx" #Replace with your actual Plex token
      - "WEBHOOK_PORT=8765" #Port to listen for webhooks
      - "WHISPER_MODEL=large-v3" #tiny, base, small, medium, large, large-v2, large-v3, large-v3-turbo. Recommended: large-v3 for accuracy
      - "WHISPER_DEVICE=cuda" #cpu or cuda for Nvidia GPU's
      - "WHISPER_COMPUTETYPE=float16" #Recommended: int8 for cpu or float16 for cuda
      - "WHISPER_CPUTHREADS=2" #Number of CPU threads to use (only applicable for cpu)
      - "WHISPER_TASK=translate" #transcribe or translate
      - "SKIP_LANGUAGES=en" #Example: 'en, de, fr'
      - "SKIP_SUB_LANGUAGES=en" #Example: 'en, de, fr'
      - "DEBUG_LOGGING=False" #Set to True to enable debug logging
    restart: unless-stopped
```

### Plex 
**Webhook**

Plex Webhooks are configured under "Account Settings" -> "Webhooks" in the Plex Web App (the Account Settings can be found under the top right user menu).
Add a new Webhook and set the url to your autosub hostname/ip address, for example: `http://127.0.0.1:8765/webhook`.
> [!NOTE]
> If you are not receiving `library.new` webhook events, make sure push notifications are turned on for your Plex Server (don't ask me why).

**Plex Token**

You need to add your Plex authentication token to the config variables in order for autosub to work.
Finding your token is pretty simple:
1. Sign in to your Plex account in Plex Web App.
2. Browse to a library item and view the XML for it.
3. Look in the URL and find the token as the X-Plex-Token value.
 
[More info](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)


### Variables
| Variable           | Default                    | Description                                                |
|--------------------|----------------------------|------------------------------------------------------------|
| `PLEX_URL`         | `http://127.0.0.1:32400`    | Plex server URL including `http(s)://` and port.           |
| `PLEX_TOKEN`       | (None)                     | Your Plex token. Must be provided.                         |
| `WEBHOOK_PORT`     | `8765`                     | Port for the Flask server to listen for webhooks.         |
| `WHISPER_MODEL`    | `large-v3`                 | Whisper model size. Options: `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`, `large-v3-turbo`. Recommended: `large-v3` for accuracy. |
| `WHISPER_DEVICE`   | `cuda`                     | Compute device for Whisper. Options: `cpu` or `cuda` for Nvidia GPU's. Recommended: `cuda` for significantly faster transcription speeds. Note: using `cuda` requires cuBLAS and cuDNN 8 for CUDA 12 installed. |
| `WHISPER_COMPUTETYPE` | `float16`                | Precision type for model computation. Recommended: `int8` for `cpu` (balances speed/memory) or `float16` for `cuda` (optimal GPU performance). |
| `WHISPER_CPUTHREADS` | `2`                       | Number of CPU threads to use (only applicable for CPU).   |
| `WHISPER_TASK`       | `translate`                | Whisper task. Options: `transcribe` (transcribes in the original audio language) or `translate` (transcribes and translates the audio directly into English). |
| `SKIP_LANGUAGES`    | `en`                    | Comma seperated list containing audio languages for which you do **NOT** want to generate subtitles. Supports two-letter and three-letter lowercase abbreviation, see [ISO 639](https://en.wikipedia.org/wiki/ISO_639). Set to `None` to generate subtitles for all audio languages. Example: `eng, de, nl`.                     |
| `SKIP_SUB_LANGUAGES`    | `en`                    | Comma seperated list containing subtitle languages. Will **NOT** generate a subtitle if the file has an existing subtitle matching this two-letter or three-letter lowercase abbreviation, see [ISO 639](https://en.wikipedia.org/wiki/ISO_639). Set to `None` to generate subtitles regardless of existing subtitles. Example: `eng, de, nl`.                     |
| `DEBUG_LOGGING`    | `False`                    | Set to `True` to enable debug logging.                     |
| `WEBHOOK_EXECUTOR_MAX_WORKERS` | `1` | Controls the max concurrent background transcription tasks. Because `faster-whisper` is highly CPU/GPU bound, concurrency > 1 may cause conflicts or out-of-memory errors. The Flask/Gunicorn server will rapidly accept incoming webhooks and queue them here to be processed sequentially. Leave at `1`. |

## Backlog
- [x] Add configurable option to skip transcribing based on existing audio languages.
- [x] Add configurable option to skip transcribing based on existing subtitle languages.
- [x] Improve audio stream detection/selection.
- [x] Remove dependency on access to Plex media paths.
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
