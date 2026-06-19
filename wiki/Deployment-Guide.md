# AutoSub Detailed Deployment Guide

Welcome to the ultimate deployment guide for **AutoSub**! This guide is designed for beginners who have never deployed a system like this before. It will walk you through every detail of configuring your environment, deploying using Docker (both prebuilt and custom built), and setting up the script manually.

AutoSub connects directly to your Plex server via the network to detect newly added media, determine its audio language, generate English subtitles for non-English audio, and upload them back to your Plex server.

> **🚀 Quick-Start for Experienced Users:**
> 1. Copy `docker-compose.yml` and `.env.example` (rename to `.env`) from the repo.
> 2. Fill in `.env` with your `PLEX_URL` and `PLEX_TOKEN` (found via "View XML" on any Plex media item).
> 3. Run `docker compose up -d`.
> 4. Add the AutoSub Webhook (`http://YOUR_DOCKER_IP:8765/webhook`) in your Plex Account Settings -> Webhooks.

---

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Finding your Plex Token](#2-finding-your-plex-token)
3. [Deployment Method A: Prebuilt Docker Image (Recommended)](#3-deployment-method-a-prebuilt-docker-image-recommended)
4. [Deployment Method B: Build Your Own Custom Docker Image](#4-deployment-method-b-build-your-own-custom-docker-image)
5. [Deployment Method C: Manual Installation](#5-deployment-method-c-manual-installation)
6. [Configuring Plex Webhooks](#6-configuring-plex-webhooks)
7. [Environment Variables Explained](#7-environment-variables-explained)
8. [Common Pitfalls](#8-common-pitfalls)
9. [Backup, Recovery, and Updates](#9-backup-recovery-and-updates)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

Before starting, make sure you have the following ready:
- **A running Plex Media Server** (you will need its URL, e.g., `http://192.168.1.100:32400`).
- **Plex Pass (Highly Recommended):** Webhooks are generally a Plex Pass feature. Check Plex documentation for your specific account setup.
- **Docker and Docker Compose installed** (If using the Docker deployment methods). For Windows users, we recommend installing **Docker Desktop** and ensuring WSL2 integration is enabled.
  - *If you are planning to use an NVIDIA GPU for transcription*, you will need the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed so Docker can access your GPU (on Windows, Docker Desktop with WSL2 handles this natively).
- **A text editor** (like Notepad, TextEdit, VSCode, or nano) to modify configuration files.
- Basic understanding of terminal/command prompt. Don't worry, we'll provide the exact commands!

---

## 2. Finding your Plex Token

AutoSub requires a Plex Token to communicate with your Plex server. Without it, the script cannot download the media to transcribe or upload the final subtitles.

**Step-by-step to find your token:**
1. Open your web browser and navigate to your Plex Web App (e.g., `app.plex.tv` or your local IP).
2. Sign in with your Plex account.
3. Browse to any library (Movies or TV Shows) and click on a specific media item (a movie or an episode).
4. Click the three dots (More options) on the top right of the media page.
5. Select **"Get Info"**.
6. At the bottom of the pop-up window, click **"View XML"**.
7. A new browser tab will open showing XML code. Look at the very top address bar.
8. In the URL, locate `X-Plex-Token=xxxxxxxxxxxxxx`. The `xxxxxxxxxxxxxx` part is your Plex Token.
9. **Copy this token and keep it safe.** Do not share it!

*Supporting Documentation:* [Finding an authentication token / X-Plex-Token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)

---

## 3. Deployment Method A: Prebuilt Docker Image (Recommended)

Using the prebuilt Docker image is the easiest and fastest way to get AutoSub running. It includes everything needed to run on either CPU or NVIDIA GPU.

### Step 3.1: Create a Project Directory
Open your terminal (or command prompt) and create a folder for AutoSub:
```bash
mkdir autosub
cd autosub
```

### Step 3.2: Create the `docker-compose.yml` File
Create a new file named `docker-compose.yml` in this directory:
```bash
nano docker-compose.yml
```

### Step 3.3: Configure `docker-compose.yml`
Copy and paste the following into your `docker-compose.yml` file. **Make sure to change the values for `PLEX_URL` and `PLEX_TOKEN`.**

```yaml
version: '3.3'
services:
  autosub:
    container_name: autosub
    # Note: For production stability, it is recommended to pin a specific version tag
    # instead of 'latest' (e.g., themclg/autosub:v1.0.0) if tags are available.
    image: themclg/autosub:latest
    hostname: autosub
    ports:
      - "8765:8765"
    environment:
      # --- REQUIRED ---
      - "PLEX_URL=http://YOUR_PLEX_IP:32400" # e.g. http://192.168.1.100:32400
      - "PLEX_TOKEN=YOUR_PLEX_TOKEN_HERE"
      - "WEBHOOK_PORT=8765"

      # --- AI SETTINGS ---
      - "WHISPER_MODEL=large-v3" # We recommend large-v3 for highest accuracy
      - "WHISPER_DEVICE=cpu" # Change to 'cuda' if you have an NVIDIA GPU
      - "WHISPER_COMPUTETYPE=int8" # 'int8' for CPU, 'float16' for cuda
      - "WHISPER_CPUTHREADS=4" # Adjust based on your CPU
      - "WHISPER_TASK=translate" # 'translate' forces English. 'transcribe' keeps original language

      # --- FILTER SETTINGS ---
      - "SKIP_LANGUAGES=en" # Do not process English audio
      - "SKIP_SUB_LANGUAGES=en" # Skip if an English subtitle already exists

      # --- ADVANCED ---
      - "DEBUG_LOGGING=False"

    # If using an NVIDIA GPU, uncomment the lines below to pass your GPU to the container:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

    restart: unless-stopped
```
Save and close the file.

### Step 3.4: Start the Container
Run the following command to download the image and start AutoSub in the background:
```bash
docker compose up -d
```
Check the logs to ensure it started successfully:
```bash
docker compose logs -f
```
You should see output indicating that the Flask server is running on port `8765`.

### Step 3.5: Post-Deployment Health Check
To verify your container is running correctly, you can perform a quick health check from your terminal:
```bash
curl http://localhost:8765/health
```
*(If the `/health` endpoint is not defined, you can look for the "Running on http://..." message in the container logs).*

Proceed to **[Section 6: Configuring Plex Webhooks](#6-configuring-plex-webhooks)**.

---

## 4. Deployment Method B: Build Your Own Custom Docker Image

If you want absolute control over the code, or you've made local modifications to the script, you can build the Docker image yourself. This means you will download the source code, tell Docker to compile it into an image on your machine, and then run *that* image.

### Step 4.1: Clone the Source Code
You need `git` installed to clone the repository. Open your terminal and run:
```bash
git clone https://github.com/TheMCLG/autosub.git
cd autosub
```

### Step 4.2: Modify Code (Optional)
If you want to edit `autosub.py`, `tasks.py`, or any other file, do it now.

### Step 4.3: Build the Docker Image
Instead of downloading the image from Docker Hub, we will build it from the `Dockerfile` present in the folder.
Run the following command:
```bash
docker build -t my-custom-autosub:latest .
```
- `docker build`: The command to build an image.
- `-t my-custom-autosub:latest`: This tags (names) your new image `my-custom-autosub` with the version `latest`.
- `.`: The dot at the end is crucial! It tells Docker to look for the `Dockerfile` in the *current directory*.

This process may take a few minutes as it downloads the base NVIDIA CUDA image and installs all Python dependencies.

### Step 4.4: Update `docker-compose.yml` to use your local image
Open the `docker-compose.yml` file located in the folder:
```bash
nano docker-compose.yml
```
Find the line that says:
```yaml
image: themclg/autosub:latest
```
And change it to the name you just created:
```yaml
image: my-custom-autosub:latest
```
Also, ensure you configure your `PLEX_URL`, `PLEX_TOKEN`, and other environment variables just like in Method A.
*(If you are modifying the code locally frequently, you can also mount your local code into the container using `volumes`, but building the image encapsulates it perfectly).*

### Step 4.5: Start your Custom Container
Run:
```bash
docker compose up -d
```
Check the logs to verify it is running your custom build:
```bash
docker compose logs -f
```
Proceed to **[Section 6: Configuring Plex Webhooks](#6-configuring-plex-webhooks)**.

---

## 5. Deployment Method C: Manual Installation

If you prefer not to use Docker, you can run AutoSub directly on your host machine (Linux, macOS, or Windows).

> **Important:** If you want to use an NVIDIA GPU, you MUST have `cuBLAS` for CUDA 12 and `cuDNN 8` for CUDA 12 installed on your system.

### Step 5.1: Install System Dependencies
You need Python 3, pip, and `ffmpeg` installed on your system.
- **Ubuntu/Debian:** `sudo apt update && sudo apt install python3 python3-pip ffmpeg git -y`
- **macOS (using Homebrew):** `brew install python ffmpeg git`
- **Windows:**
  1. Download and install Python from [python.org](https://www.python.org/downloads/) (Make sure to check "Add Python to PATH" during installation).
  2. Download FFmpeg from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or install via winget: `winget install ffmpeg`. Ensure the `bin` folder is added to your system's Environment Variables (PATH).
  3. Install Git from [git-scm.com](https://git-scm.com/download/win).

### Step 5.2: Clone the Repository
```bash
git clone https://github.com/TheMCLG/autosub.git
cd autosub
```

### Step 5.3: Install Python Dependencies
It is highly recommended to use a virtual environment, but for simplicity:
```bash
pip3 install -r requirements.txt
```

### Step 5.4: Configure Variables
You have two options to configure variables for a manual run:
1. **Export them to your environment:**
   ```bash
   export PLEX_URL="http://192.168.1.100:32400"
   export PLEX_TOKEN="xxxxxxxxxxxxxx"
   export WHISPER_DEVICE="cpu"
   # ... export others ...
   ```
2. **Edit the Python files directly:** You can edit the default values in `autosub.py` and `tasks.py` if you prefer hardcoding them (not recommended but functional).

### Step 5.5: Run AutoSub
For a quick test, run:
```bash
python3 -u autosub.py
```
**For production (Linux/macOS):** It is highly recommended to use the included `run.sh` script which uses Gunicorn. Gunicorn is a robust server manager. Run it via:
```bash
chmod +x run.sh
./run.sh
```
This script ensures only one worker (`-w 1`) is running to prevent multiple models from loading into GPU memory and crashing your system.

Proceed to **[Section 6: Configuring Plex Webhooks](#6-configuring-plex-webhooks)**.

---

## 6. Configuring Plex Webhooks

AutoSub relies on Plex telling it when new media is added. This is done via Webhooks.

1. Open your web browser and sign in to the **Plex Web App**.
2. Click the **Wrench icon (Settings)** in the top right corner.
3. On the left sidebar, under **Account Settings**, click on **Webhooks** (You may need to click your profile picture/account name on the top right -> Account Settings -> Webhooks).
4. Click **"Add Webhook"**.
5. In the URL field, enter the URL of the machine running AutoSub, pointing to the `/webhook` endpoint.
   - For example, if your Docker container is running on a machine with IP `192.168.1.50` and the port is `8765`, you will enter:
     `http://192.168.1.50:8765/webhook`
6. Click **Save Changes**.

**Testing:**
Add a new movie or TV show to your Plex server. Watch the AutoSub logs (`docker compose logs -f` or your terminal output). You should see AutoSub receive a `library.new` event and begin processing!

> **Note:** If AutoSub receives the webhook but doesn't start processing, ensure push notifications are turned on for your Plex Server in the Plex settings.

> **Security Note:** It is highly recommended to keep AutoSub on your local network. Do **not** expose port `8765` directly to the public internet. If you need to access it remotely or if your Plex server is hosted externally, consider using a VPN (like Tailscale or WireGuard) or placing AutoSub behind a secure Reverse Proxy with strict access controls.

---

## 7. Environment Variables Explained

Here is a detailed breakdown of what every variable does:

| Variable | Description |
|---|---|
| `PLEX_URL` | The full URL to your Plex server, including `http://` or `https://` and the port (usually `:32400`). |
| `PLEX_TOKEN` | The authentication token you found in Step 2. |
| `WEBHOOK_PORT` | The port AutoSub will listen on. Default is `8765`. If you change this, ensure your Docker port mapping and Plex Webhook URL match. |
| `WHISPER_MODEL` | The AI model used. `large-v3` is the most accurate but requires more RAM/VRAM. Options: `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`, `large-v3-turbo`. |
| `WHISPER_DEVICE` | Set to `cuda` if you have an NVIDIA GPU passed to the container. Otherwise, set to `cpu`. |
| `WHISPER_COMPUTETYPE` | How the model calculates. Use `int8` for `cpu` (saves memory/increases speed). Use `float16` for `cuda` (best GPU performance). |
| `WHISPER_CPUTHREADS` | How many CPU cores to allocate if `WHISPER_DEVICE=cpu`. e.g., `4`. |
| `WHISPER_TASK` | `translate` will transcribe audio and translate it into English. `transcribe` will just transcribe in the original language. |
| `SKIP_LANGUAGES` | Comma-separated list of languages to IGNORE. E.g., `en`. If the audio is English, it won't generate subs. |
| `SKIP_SUB_LANGUAGES` | Comma-separated list of existing subtitle languages. If an `en` subtitle already exists on the file, it will skip processing. |
| `DEBUG_LOGGING` | Set to `True` to see much more detailed logs in the console. Excellent for troubleshooting. |
| `WEBHOOK_EXECUTOR_MAX_WORKERS` | Leave this at `1`. Running multiple transcription jobs at the same time will likely crash your GPU/CPU due to memory exhaustion. |

---

## 8. Common Pitfalls

Here are some frequent mistakes users make during initial setup:
- **Mixing up `localhost` / `127.0.0.1` in Docker:** If you run AutoSub in Docker and set your `PLEX_URL` to `http://127.0.0.1:32400`, the container will look for Plex *inside* the container, which will fail. Always use your host machine's actual IP (e.g., `192.168.1.50`).
- **Forgetting to Expose Ports:** If you change `WEBHOOK_PORT` to something other than `8765`, make sure you also update the `ports:` mapping in your `docker-compose.yml` (e.g., `"9000:9000"`).
- **No Plex Pass:** While you might find the Webhook settings page, Webhooks are officially a Plex Pass feature. If webhooks are silently failing to trigger, verify your Plex Pass status.
- **Copy/Paste Errors in Configuration:** Missing quotes or extra spaces in your `PLEX_TOKEN` or `PLEX_URL` can cause immediate failure. We provide an `.env.example` file in the repository root you can copy to avoid typos!

---

## 9. Backup, Recovery, and Updates

- **Backups:** Because AutoSub operates entirely statelessly via the Plex API, there is no internal database or configuration file to backup other than your `docker-compose.yml` and environment variables. To back up your setup, simply copy your `docker-compose.yml` to a safe location.
- **Updating Docker Image:** If using Method A, simply pull the latest image and recreate the container:
  ```bash
  docker compose pull
  docker compose up -d
  ```
- **Updating Custom Image:** If using Method B, pull the latest code and rebuild:
  ```bash
  git pull
  docker build -t my-custom-autosub:latest .
  docker compose up -d
  ```

---

## 10. Troubleshooting

**Issue: "Connection Refused" or Webhooks not arriving.**
- *Fix:* Ensure the IP address in your Plex Webhook settings matches the machine running AutoSub. Ensure port `8765` is open on any firewalls.

**Issue: GPU is not being used / Out of Memory errors.**
- *Fix:* Ensure you uncommented the `deploy` -> `resources` section in `docker-compose.yml` to pass the GPU. Check that `WHISPER_DEVICE=cuda`. If it runs out of memory, try a smaller model like `small` or `base`.

**Issue: "Unauthorized" errors when trying to read media.**
- *Fix:* Double-check your `PLEX_TOKEN`. Tokens can sometimes reset if you change your Plex password or sign out all devices.

**Issue: The container keeps restarting.**
- *Fix:* Run `docker compose logs` to see the error. It's usually a misconfigured environment variable or missing Plex URL/Token.

---
*Happy Transcribing!*
