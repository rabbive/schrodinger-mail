# Schrödinger Mail — compact production image for Heroku
# =======================================================
# Stage 1 builds only ML-KEM-768 and ML-DSA-65, keeping compile time and image
# size far below a full liboqs build. Stage 2 builds the React SPA. Stage 3 runs
# both UI and API from one small dyno.

FROM python:3.12-slim AS liboqs-builder

ARG LIBOQS_VERSION=0.16.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates cmake git libssl-dev ninja-build \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch "${LIBOQS_VERSION}" \
      https://github.com/open-quantum-safe/liboqs.git /tmp/liboqs \
    && cmake -S /tmp/liboqs -B /tmp/liboqs/build -GNinja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr/local \
      -DBUILD_SHARED_LIBS=ON \
      -DOQS_BUILD_ONLY_LIB=ON \
      -DOQS_DIST_BUILD=ON \
      -DOQS_MINIMAL_BUILD="KEM_ml_kem_768;SIG_ml_dsa_65" \
    && cmake --build /tmp/liboqs/build --parallel \
    && cmake --install /tmp/liboqs/build \
    && find /usr/local/lib -maxdepth 1 -type f -name 'liboqs.so*' \
      -exec strip --strip-unneeded {} +


FROM node:22-alpine AS frontend-builder

WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN npm --prefix frontend ci --no-audit --no-fund
COPY frontend ./frontend
RUN npm --prefix frontend run build


FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libpq5 libssl3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=liboqs-builder /usr/local/lib/liboqs.so* /usr/local/lib/
RUN ldconfig

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-builder /src/static ./static

ENV QEC_PORT=5001 \
    QEC_DEBUG=0 \
    QEC_LOG_LEVEL=INFO \
    QEC_LOG_FORMAT=json \
    PYTHONUNBUFFERED=1 \
    WEB_CONCURRENCY=1

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', os.environ.get('QEC_PORT', '5001')) + '/healthz')" || exit 1

# One worker is intentional: cheapest dyno, SQLite-safe, and compatible with
# Flask-SocketIO's in-memory room state. Heroku supplies PORT at runtime.
CMD ["sh", "-c", "exec gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker --workers ${WEB_CONCURRENCY:-1} --bind 0.0.0.0:${PORT:-5001} --timeout 120 --access-logfile - --error-logfile - app:app"]
