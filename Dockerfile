# Lightweight Python base image
FROM python:3.12-slim

LABEL org.opencontainers.image.title="immich-face-to-album"
LABEL org.opencontainers.image.description="Periodic Immich face-to-album synchronization CLI container"
LABEL org.opencontainers.image.source="https://github.com/romainrbr/immich-face-to-album"
LABEL org.opencontainers.image.licenses="WTFPL"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt || true

COPY . /app

RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "immich_face_to_album"]
