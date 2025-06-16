FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    build-essential \
    cmake \
    libyaml-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Clone and build rtmp_relay
RUN git clone https://github.com/elnormous/rtmp_relay.git /tmp/rtmp_relay && \
    cd /tmp/rtmp_relay && \
    git submodule update --init && \
    make && \
    cp bin/rtmp_relay /usr/local/bin/ && \
    rm -rf /tmp/rtmp_relay

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    aiohttp \
    pyyaml

# Copy node client script
COPY scripts/node_client.py /app/node_client.py
RUN chmod +x /app/node_client.py

# Create non-root user
RUN useradd -m -u 1000 streamr && chown -R streamr:streamr /app
USER streamr

# Expose RTMP and stats ports
EXPOSE 1935 8080

# Set entrypoint
ENTRYPOINT ["python3", "/app/node_client.py"] 