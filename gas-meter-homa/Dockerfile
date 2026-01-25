# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
ARG BUILD_ARCH=amd64
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-debian:latest
FROM $BUILD_FROM

RUN echo "alias l='ls --color=auto -alF'" >> /root/.bashrc

# Install dependencies
RUN apt-get update && \
    apt-get install -y git python3-venv python3-paho-mqtt python3-libgpiod gpiod

# Install hass-addon-helper from Git
# RUN \
#     mkdir -p /usr/local/src && \
#     git -C /usr/local/src clone --depth 1 --branch main https://github.com/hass-hmueller01/hass-addon-helper.git
#     pip3 install --no-cache-dir --root-user-action ignore --break-system-packages \
#         git+https://github.com/hass-hmueller01/hass-addon-helper.git@main

# Copy root filesystem
COPY rootfs /

# Build the Python virtual environment for the service
RUN \
    cd /etc/services.d/gas-meter && \
    python3 -m venv .venv --system-site-packages && \
    source .venv/bin/activate && \
    pip3 install --upgrade pip && \
    pip3 install -r requirements.txt

# Cleanup
RUN apt-get remove -y git && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /usr/local/src/hass-addon-helper

ENTRYPOINT ["/init"]
