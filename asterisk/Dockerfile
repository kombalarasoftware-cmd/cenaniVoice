FROM debian:bullseye-slim AS builder

LABEL maintainer="VoiceAI Platform"

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    git \
    subversion \
    libncurses5-dev \
    libssl-dev \
    libxml2-dev \
    libsqlite3-dev \
    uuid-dev \
    libjansson-dev \
    libsrtp2-dev \
    libedit-dev \
    libxslt1-dev \
    libspandsp-dev \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

# Download and build Asterisk 20
WORKDIR /usr/src
RUN wget https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-20-current.tar.gz \
    && tar xzf asterisk-20-current.tar.gz \
    && cd asterisk-20.* \
    && (contrib/scripts/get_mp3_source.sh || true) \
    && ./configure --with-jansson-bundled \
    && make menuselect.makeopts \
    && menuselect/menuselect --enable codec_opus \
    && menuselect/menuselect --enable chan_audiosocket \
    && menuselect/menuselect --enable app_audiosocket \
    && menuselect/menuselect --enable res_ari \
    && menuselect/menuselect --enable res_ari_applications \
    && menuselect/menuselect --enable res_ari_asterisk \
    && menuselect/menuselect --enable res_ari_bridges \
    && menuselect/menuselect --enable res_ari_channels \
    && menuselect/menuselect --enable res_ari_device_states \
    && menuselect/menuselect --enable res_ari_endpoints \
    && menuselect/menuselect --enable res_ari_events \
    && menuselect/menuselect --enable res_ari_mailboxes \
    && menuselect/menuselect --enable res_ari_playbacks \
    && menuselect/menuselect --enable res_ari_recordings \
    && menuselect/menuselect --enable res_ari_sounds \
    && menuselect/menuselect --enable res_stasis \
    && menuselect/menuselect --enable res_stasis_answer \
    && menuselect/menuselect --enable res_stasis_device_state \
    && menuselect/menuselect --enable res_stasis_playback \
    && menuselect/menuselect --enable res_stasis_recording \
    && menuselect/menuselect --enable res_stasis_snoop \
    && menuselect/menuselect --enable res_http_websocket \
    && make \
    && make install \
    && make samples \
    && make config \
    && ldconfig

# ========================================
# Runtime Stage - sadece config değişince rebuild olmaz
# ========================================
FROM debian:bullseye-slim AS runtime

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libncurses5 \
    libssl1.1 \
    libxml2 \
    libsqlite3-0 \
    libuuid1 \
    libjansson4 \
    libsrtp2-1 \
    libedit2 \
    libxslt1.1 \
    libspandsp2 \
    libopus0 \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled Asterisk from builder
COPY --from=builder /usr/sbin/asterisk /usr/sbin/asterisk
COPY --from=builder /usr/lib/asterisk/ /usr/lib/asterisk/
COPY --from=builder /usr/lib/libasterisk* /usr/lib/
COPY --from=builder /var/lib/asterisk/ /var/lib/asterisk/
COPY --from=builder /var/spool/asterisk/ /var/spool/asterisk/
COPY --from=builder /var/log/asterisk/ /var/log/asterisk/
COPY --from=builder /var/run/asterisk/ /var/run/asterisk/
COPY --from=builder /etc/asterisk/ /etc/asterisk/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libasterisk* /usr/lib/x86_64-linux-gnu/

RUN ldconfig

# Create asterisk user and set permissions
RUN useradd -m asterisk \
    && chown -R asterisk:asterisk /var/lib/asterisk \
    && chown -R asterisk:asterisk /var/spool/asterisk \
    && chown -R asterisk:asterisk /var/log/asterisk \
    && chown -R asterisk:asterisk /var/run/asterisk \
    && chown -R asterisk:asterisk /etc/asterisk

# Copy configuration files
COPY pjsip.conf /etc/asterisk/pjsip.conf
COPY extensions.conf /etc/asterisk/extensions.conf
COPY ari.conf /etc/asterisk/ari.conf
COPY http.conf /etc/asterisk/http.conf
COPY rtp.conf /etc/asterisk/rtp.conf
COPY amd.conf /etc/asterisk/amd.conf

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set permissions
RUN chown asterisk:asterisk /etc/asterisk/*.conf

# Create recordings directory
RUN mkdir -p /var/spool/asterisk/recording \
    && chown asterisk:asterisk /var/spool/asterisk/recording

# Expose ports
# SIP
EXPOSE 5060/udp
EXPOSE 5060/tcp
# SIP TLS
EXPOSE 5061/tcp
# RTP
EXPOSE 10000-10100/udp
# HTTP/ARI
EXPOSE 8088/tcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD asterisk -rx "core show version" || exit 1

# Entrypoint runs as root to modify configs, then drops to asterisk user
ENTRYPOINT ["docker-entrypoint.sh"]

# Start Asterisk in foreground
CMD ["asterisk", "-f", "-U", "asterisk", "-G", "asterisk", "-vvv"]
