FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04
WORKDIR /autosub
RUN apt-get update && apt-get install -y python3 python3-pip ffmpeg
RUN pip install flask
RUN pip install stable-ts
RUN pip install faster-whisper
RUN pip install requests
ENV PYTHONUNBUFFERED 1
COPY autosub.py .
CMD ["python3", "-u", "autosub.py"]
EXPOSE 8765