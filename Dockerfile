FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04
WORKDIR /autosub
RUN apt-get update && apt-get install -y python3 python3-pip ffmpeg
COPY requirements.txt .
RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED 1
COPY autosub.py .
COPY tasks.py .
COPY run.sh .
RUN chmod +x run.sh
CMD ["./run.sh"]
EXPOSE 8765
