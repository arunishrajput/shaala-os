FROM python:3.11-slim

# Minimal shared libs opencv-python-headless needs at import time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

EXPOSE 8000

# --forwarded-allow-ips="*" trusts Render's edge proxy to set X-Forwarded-For.
# Without it, uvicorn's client info is the proxy's own address for every
# request, so slowapi's IP-keyed rate limits (app/limiter.py) would bucket
# all users behind Render together instead of limiting per real client.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
