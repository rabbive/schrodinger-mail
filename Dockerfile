# Schrödinger Mail — Docker Image
# ============================================
# Multi-stage build: stage 1 compiles liboqs, stage 2 runs the app.

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Build liboqs from source
RUN git clone --depth 1 --branch 0.12.0 https://github.com/open-quantum-safe/liboqs.git /tmp/liboqs \
    && cd /tmp/liboqs && mkdir build && cd build \
    && cmake -GNinja .. -DCMAKE_INSTALL_PREFIX=/usr/local -DBUILD_SHARED_LIBS=ON \
    || cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local -DBUILD_SHARED_LIBS=ON \
    && make -j$(nproc) && make install \
    && rm -rf /tmp/liboqs

# ---------- Runtime stage ----------
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy liboqs shared libraries
COPY --from=builder /usr/local/lib/liboqs* /usr/local/lib/
COPY --from=builder /usr/local/include/oqs /usr/local/include/oqs
RUN ldconfig

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

ENV QEC_SECRET_KEY=change-me-in-production
ENV QEC_JWT_SECRET=change-me-in-production
ENV QEC_PORT=5001
ENV QEC_DEBUG=0
ENV QEC_LOG_LEVEL=INFO
ENV QEC_LOG_FORMAT=json
ENV QEC_METRICS=1
ENV PYTHONUNBUFFERED=1

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/api/auth/status')" || exit 1

CMD ["python", "app.py"]
