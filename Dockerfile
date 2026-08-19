FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    CHAT_HTTP_HOST=0.0.0.0 \
    CHAT_HTTP_PORT=8091

WORKDIR /app

RUN groupadd --system --gid 10001 chatbot \
    && useradd --system --uid 10001 --gid chatbot --home-dir /nonexistent --shell /usr/sbin/nologin chatbot

COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir --requirement requirements-runtime.txt

COPY --chown=chatbot:chatbot src ./src

USER 10001:10001
EXPOSE 8091

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import json,urllib.request; response=urllib.request.urlopen('http://127.0.0.1:8091/healthz', timeout=2); assert response.status == 200 and json.load(response) == {'status': 'ok'}"

CMD ["python", "-m", "app.chat_runtime.http_server"]
