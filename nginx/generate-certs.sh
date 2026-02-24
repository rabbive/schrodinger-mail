#!/bin/bash
# Generate self-signed TLS certificates for development.
# For production, use Let's Encrypt / certbot.

set -euo pipefail

CERT_DIR="$(dirname "$0")/certs"
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/fullchain.pem" ] && [ -f "$CERT_DIR/privkey.pem" ]; then
    echo "Certificates already exist in $CERT_DIR"
    exit 0
fi

echo "Generating self-signed TLS certificate..."
openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout "$CERT_DIR/privkey.pem" \
    -out "$CERT_DIR/fullchain.pem" \
    -subj "/CN=localhost/O=SchrodingerMail/C=US" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "Certificates generated in $CERT_DIR"
