# Filtering HTTPS proxy for ResearchCode Phase 4 agent containers.
#
# Agent containers sit on an internal Docker network with no route to the internet. This
# proxy is the only way out, and it allows CONNECT only to the hosts in `allowlist`
# (the model API and the Python package index). GitHub and other sites are refused, so
# an agent cannot download this repository's hidden evaluator.
#
# Build: rc-exp build-images   (tag researchcode-proxy:1)

# debian:bookworm-slim, pinned by digest
FROM debian@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc

RUN apt-get update \
    && apt-get install -y --no-install-recommends tinyproxy \
    && rm -rf /var/lib/apt/lists/*
COPY tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY allowlist /etc/tinyproxy/allowlist
EXPOSE 8888
CMD ["tinyproxy", "-d", "-c", "/etc/tinyproxy/tinyproxy.conf"]
