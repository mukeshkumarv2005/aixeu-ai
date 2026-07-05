#!/usr/bin/env bash
# Automate SSL certification using Let's Encrypt Certbot.
# Handles the chicken-and-egg boot problem by bootstrapping self-signed certs first.
set -euo pipefail

# Root checks
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root (using sudo)."
  exit 1
fi

echo "=== Aevix Let's Encrypt SSL Bootstrapper ==="
echo ""

# Get Domain and Email
read -rp "Enter your deployment domain (e.g., app.aevix.ai): " DOMAIN
if [ -z "$DOMAIN" ]; then
  echo "Error: Domain name cannot be empty."
  exit 1
fi

read -rp "Enter email for renewal notifications: " EMAIL
if [ -z "$EMAIL" ]; then
  echo "Error: Email address cannot be empty."
  exit 1
fi

# Dry run / Staging choice
read -rp "Enable staging certificate (dry-run/testing)? [y/N]: " STAGING_ANS
STAGING=0
if [[ "$STAGING_ANS" =~ ^[Yy]$ ]]; then
  STAGING=1
  echo "Using staging environment..."
fi

# Define paths
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
mkdir -p "/etc/letsencrypt/live"

# Check if certificates already exist
if [ -d "$CERT_DIR" ]; then
  read -rp "Certificates for $DOMAIN already exist. Re-create them? [y/N]: " OVERWRITE
  if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
    echo "Exiting without changes."
    exit 0
  fi
fi

echo "→ Step 1: Bootstrapping temporary self-signed certificate for $DOMAIN..."
TEMP_DIR="/etc/letsencrypt/live/localhost"
mkdir -p "$TEMP_DIR"

openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout "$TEMP_DIR/privkey.pem" \
  -out "$TEMP_DIR/fullchain.pem" \
  -subj "/CN=localhost" \
  -quiet

echo "→ Step 2: Booting Nginx with temporary certificates..."
# Ensure the production compose configuration points to Nginx configuration
# Copy SSL config over the normal default nginx configuration inside docker
cp docker/nginx/nginx.ssl.conf docker/nginx/nginx.conf

# Map host folder paths dynamically
# Replace live/localhost in nginx config with domain to match live paths
sed -i "s|live/localhost|live/$DOMAIN|g" docker/nginx/nginx.conf

docker compose up -d nginx

echo "→ Step 3: Acquiring real certificate from Let's Encrypt using Certbot Webroot..."
# Run certbot in a temporary docker container or on host if available
# We run certbot docker container sharing volumes
STAGING_FLAG=""
if [ "$STAGING" -eq 1 ]; then
  STAGING_FLAG="--staging"
fi

# Execute Certbot container to fetch the certificate
docker run --rm \
  -v "/etc/letsencrypt:/etc/letsencrypt" \
  -v "/var/lib/letsencrypt:/var/lib/letsencrypt" \
  -v "$(pwd)/storage/certbot:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d "$DOMAIN" \
  --email "$EMAIL" \
  --rsa-key-size 4096 \
  --agree-tos \
  --no-eff-email \
  $STAGING_FLAG \
  --non-interactive \
  --force-renewal

echo "→ Step 4: Activating live Let's Encrypt certificates..."
# Copy real certificates to the active domain path if certbot put it elsewhere
# Certbot automatically creates /etc/letsencrypt/live/<domain>/ fullchain and privkey.
# If they exist, we delete the self-signed backup
rm -rf "$TEMP_DIR"

echo "→ Step 5: Reloading Nginx to load the production certificates..."
docker compose exec nginx nginx -s reload

echo ""
echo "=========================================================="
echo "SUCCESS: SSL certificates provisioned for https://$DOMAIN"
echo "Automatic Certbot renewal setup instructions: "
echo "Add this cronjob to renew certificates: "
echo "0 0 * * * docker run --rm -v /etc/letsencrypt:/etc/letsencrypt -v /var/lib/letsencrypt:/var/lib/letsencrypt -v $(pwd)/storage/certbot:/var/www/certbot certbot/certbot renew --webroot -w /var/www/certbot && docker compose exec -T nginx nginx -s reload"
echo "=========================================================="
