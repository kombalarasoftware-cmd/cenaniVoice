FROM debian:bullseye-slim

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
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8088/ari/api-docs/resources.json \
    --user voiceai:voiceai_ari_secret || exit 1

# Run as asterisk user
USER asterisk

# Start Asterisk in foreground
CMD ["asterisk", "-f", "-vvv"]
