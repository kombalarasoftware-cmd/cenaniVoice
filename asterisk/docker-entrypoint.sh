#!/bin/bash
# =============================================================================
# Asterisk Docker Entrypoint
# Replaces configuration placeholders with environment variables at runtime
# =============================================================================

set -e

CONFIG_DIR="/etc/asterisk"

echo "==> Asterisk entrypoint: Applying runtime configuration..."

# --- External IP ---
EXTERNAL_IP="${ASTERISK_EXTERNAL_IP:-${ASTERISK_EXTERNAL_HOST:-}}"
if [ -n "$EXTERNAL_IP" ]; then
    echo "    External IP: $EXTERNAL_IP"
    sed -i "s/__EXTERNAL_IP__/$EXTERNAL_IP/g" "$CONFIG_DIR/pjsip.conf"
else
    echo "    WARNING: No ASTERISK_EXTERNAL_IP set, removing external address lines"
    sed -i '/__EXTERNAL_IP__/d' "$CONFIG_DIR/pjsip.conf"
fi

# --- SIP Trunk Password ---
if [ -n "$SIP_TRUNK_PASSWORD" ]; then
    echo "    SIP Trunk password: configured"
    sed -i "s/__SIP_TRUNK_PASSWORD__/$SIP_TRUNK_PASSWORD/g" "$CONFIG_DIR/pjsip.conf"
else
    echo "    WARNING: SIP_TRUNK_PASSWORD not set!"
fi

# --- Ultravox SIP Password ---
if [ -n "$ULTRAVOX_SIP_PASSWORD" ]; then
    echo "    Ultravox SIP password: configured"
    sed -i "s/__ULTRAVOX_SIP_PASSWORD__/$ULTRAVOX_SIP_PASSWORD/g" "$CONFIG_DIR/pjsip.conf"
else
    echo "    WARNING: ULTRAVOX_SIP_PASSWORD not set!"
fi

# --- ARI Password (ari.conf) ---
if [ -n "$ARI_PASSWORD" ]; then
    echo "    ARI password: configured"
    sed -i "s/voiceai_ari_secret/$ARI_PASSWORD/g" "$CONFIG_DIR/ari.conf"
fi

# --- ARI Username (ari.conf) ---
if [ -n "$ARI_USERNAME" ]; then
    echo "    ARI username: $ARI_USERNAME"
    sed -i "s/^\[voiceai\]/[$ARI_USERNAME]/" "$CONFIG_DIR/ari.conf"
fi

echo "==> Configuration applied. Starting Asterisk..."

# Execute the main command (asterisk -f -vvv)
exec "$@"
