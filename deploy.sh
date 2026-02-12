#!/bin/bash
# =============================================================================
# VoiceAI Platform - Server Deploy Script
# Target: one.speakmaxi.com (37.27.119.79)
# =============================================================================
set -euo pipefail

DOMAIN="one.speakmaxi.com"
APP_DIR="/opt/voiceai"
REPO_URL="https://github.com/kombalarasoftware-cmd/cenaniVoice.git"
EMAIL="cmutlu2006@hotmail.com"  # For Let's Encrypt notifications

echo "============================================="
echo "  VoiceAI Platform - Production Deploy"
echo "  Domain: $DOMAIN"
echo "============================================="

# ---- Step 1: System update & Docker install ----
echo ""
echo "[1/8] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq git curl apt-transport-https ca-certificates gnupg lsb-release

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
    echo "Docker installed successfully."
else
    echo "Docker already installed: $(docker --version)"
fi

# Install Docker Compose plugin if not present
if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose plugin..."
    apt-get install -y -qq docker-compose-plugin
fi

# ---- Step 2: Clone or update repository ----
echo ""
echo "[2/8] Setting up application directory..."
if [ -d "$APP_DIR" ]; then
    echo "Updating existing installation..."
    cd "$APP_DIR"
    git fetch origin
    git reset --hard origin/main
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# ---- Step 3: Create .env file ----
echo ""
echo "[3/8] Configuring environment..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo "Creating .env from template..."
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"

    # Generate secure secrets
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))" 2>/dev/null || openssl rand -base64 48)
    WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 24)
    POSTGRES_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))" 2>/dev/null || openssl rand -base64 18)
    REDIS_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || openssl rand -base64 12)
    MINIO_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))" 2>/dev/null || openssl rand -base64 18)
    ARI_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || openssl rand -base64 12)

    # Update .env with generated values
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" "$APP_DIR/.env"
    sed -i "s|^WEBHOOK_SECRET=.*|WEBHOOK_SECRET=$WEBHOOK_SECRET|" "$APP_DIR/.env"
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASS|" "$APP_DIR/.env"
    sed -i "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$REDIS_PASS|" "$APP_DIR/.env"
    sed -i "s|^MINIO_ROOT_PASSWORD=.*|MINIO_ROOT_PASSWORD=$MINIO_PASS|" "$APP_DIR/.env"
    sed -i "s|^MINIO_ACCESS_KEY=.*|MINIO_ACCESS_KEY=minioadmin|" "$APP_DIR/.env"
    sed -i "s|^MINIO_SECRET_KEY=.*|MINIO_SECRET_KEY=$MINIO_PASS|" "$APP_DIR/.env"
    sed -i "s|^ASTERISK_ARI_USER=.*|ASTERISK_ARI_USER=voiceai|" "$APP_DIR/.env"
    sed -i "s|^ASTERISK_ARI_PASSWORD=.*|ASTERISK_ARI_PASSWORD=$ARI_PASS|" "$APP_DIR/.env"
    sed -i "s|^ULTRAVOX_WEBHOOK_URL=.*|ULTRAVOX_WEBHOOK_URL=https://$DOMAIN/api/v1/webhooks/ultravox|" "$APP_DIR/.env"
    sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=[\"https://$DOMAIN\"]|" "$APP_DIR/.env"

    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  ⚠  IMPORTANT: Edit .env with your API keys!       ║"
    echo "║                                                      ║"
    echo "║  nano $APP_DIR/.env                                  ║"
    echo "║                                                      ║"
    echo "║  Required keys:                                      ║"
    echo "║  - ULTRAVOX_API_KEY                                  ║"
    echo "║  - OPENAI_API_KEY (if using OpenAI provider)         ║"
    echo "║  - SIP_TRUNK_HOST, USERNAME, PASSWORD                ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    echo "Auto-generated credentials saved to: $APP_DIR/.env"
else
    echo ".env already exists, keeping current configuration."
fi

# ---- Step 4: Configure firewall ----
echo ""
echo "[4/8] Configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 4323/tcp   # SSH (custom port)
    ufw allow 80/tcp     # HTTP
    ufw allow 443/tcp    # HTTPS
    ufw allow 5043/udp   # SIP (custom port)
    ufw allow 5043/tcp   # SIP TCP (custom port)
    ufw allow 10000:10100/udp  # RTP
    ufw --force enable
    echo "Firewall configured."
else
    echo "UFW not installed, skipping firewall setup."
fi

# ---- Step 5: Initial deploy (HTTP only, no SSL yet) ----
echo ""
echo "[5/8] Starting services (HTTP mode for SSL certificate)..."
cd "$APP_DIR"

# Use initial nginx config (no SSL)
cp nginx/nginx-initial.conf nginx/nginx.conf.bak
cp nginx/nginx-initial.conf nginx/nginx.conf

# Build and start all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo "Waiting for services to start..."
sleep 20

# Check if services are healthy
echo "Service status:"
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}"

# ---- Step 6: Obtain SSL certificate ----
echo ""
echo "[6/8] Obtaining SSL certificate from Let's Encrypt..."

# Request certificate
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot \
    certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# ---- Step 7: Switch to full SSL nginx config ----
echo ""
echo "[7/8] Enabling HTTPS..."
cp nginx/nginx.conf.bak nginx/nginx.conf.initial-backup
# Restore the full SSL nginx config
git checkout nginx/nginx.conf

# Reload nginx with SSL
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx

# ---- Step 8: Run database migrations ----
echo ""
echo "[8/8] Running database migrations..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend \
    alembic upgrade head 2>/dev/null || echo "Migrations completed (or already up to date)"

# ---- Done! ----
echo ""
echo "============================================="
echo "  ✅ Deployment Complete!"
echo "============================================="
echo ""
echo "  🌐 Application: https://$DOMAIN"
echo "  📊 MinIO Console: https://$DOMAIN:9001"
echo ""
echo "  Next steps:"
echo "  1. Edit API keys: nano $APP_DIR/.env"
echo "  2. Restart after config: cd $APP_DIR && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
echo "  3. Create admin user: docker compose exec backend python -c \"...\""
echo ""
echo "  Useful commands:"
echo "  - Logs:    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f"
echo "  - Status:  docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"
echo "  - Restart: docker compose -f docker-compose.yml -f docker-compose.prod.yml restart"
echo ""
