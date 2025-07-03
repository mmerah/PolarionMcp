#!/bin/bash

# Generate SSL certificates for HTTPS development
# This script creates self-signed certificates for development/testing

set -e

# Configuration
CERT_DIR="certs"
CERT_NAME="cert"
KEY_NAME="key"
DAYS=365
COUNTRY="US"
STATE="CA"
CITY="San Francisco"
ORG="Polarion MCP"
UNIT="Development"
COMMON_NAME="localhost"

# Create certificates directory
mkdir -p "$CERT_DIR"

echo "Generating SSL certificates for HTTPS development..."

# Generate private key
openssl genrsa -out "$CERT_DIR/$KEY_NAME.pem" 2048

# Generate certificate signing request
openssl req -new -key "$CERT_DIR/$KEY_NAME.pem" -out "$CERT_DIR/$CERT_NAME.csr" -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$UNIT/CN=$COMMON_NAME"

# Generate self-signed certificate
openssl x509 -req -in "$CERT_DIR/$CERT_NAME.csr" -signkey "$CERT_DIR/$KEY_NAME.pem" -out "$CERT_DIR/$CERT_NAME.pem" -days $DAYS -extensions v3_req -extfile <(
cat <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $CITY
O = $ORG
OU = $UNIT
CN = $COMMON_NAME

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF
)

# Clean up CSR file
rm "$CERT_DIR/$CERT_NAME.csr"

# Set appropriate permissions
chmod 600 "$CERT_DIR/$KEY_NAME.pem"
chmod 644 "$CERT_DIR/$CERT_NAME.pem"

echo "SSL certificates generated successfully!"
echo "Certificate: $CERT_DIR/$CERT_NAME.pem"
echo "Private key: $CERT_DIR/$KEY_NAME.pem"
echo ""
echo "IMPORTANT: These are self-signed certificates for development only."
echo "For production, use certificates from a trusted Certificate Authority."
echo ""
echo "You can now start the HTTP server with HTTPS support:"
echo "python -m mcp_server.http_server --https --cert $CERT_DIR/$CERT_NAME.pem --key $CERT_DIR/$KEY_NAME.pem"