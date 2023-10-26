FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
WORKDIR /autosub
RUN apt-get update && apt-get install -y python3 python3-pip ffmpeg
RUN pip install flask
RUN pip install stable-ts
RUN pip install faster-whisper
RUN pip install requests
RUN pip install "celery[redis]"
ENV PYTHONUNBUFFERED 1
COPY autosub.py /autosub
COPY tasks.py /autosub
COPY utils.py /autosub
COPY run.sh /autosub
RUN chmod +x run.sh
CMD ["/autosub/run.sh"]
EXPOSE 8765