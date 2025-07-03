#!/bin/bash
# Generate self-signed certificates for the MCP Server for local HTTPS development.

CERT_DIR="mcp_server/certs"
KEY_FILE="${CERT_DIR}/key.pem"
CERT_FILE="${CERT_DIR}/cert.pem"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "Certificates already exist in ${CERT_DIR}. Skipping generation."
    exit 0
fi

echo "Generating self-signed certificates..."
mkdir -p "$CERT_DIR"

openssl req -x509 -newkey rsa:4096 -nodes -out "$CERT_FILE" -keyout "$KEY_FILE" -days 365 \
-subj "/C=US/ST=California/L=San Francisco/O=Development Corp/OU=Engineering/CN=localhost"

if [ $? -eq 0 ]; then
    echo "Successfully generated key.pem and cert.pem in ${CERT_DIR}"
else
    echo "Failed to generate certificates."
    exit 1
fi
