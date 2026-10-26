# Kernel build environment: the pinned J606L cross toolchain image plus the
# tools build-kernel.sh applies patches with.
ARG BASE=haltia-j606l-ramdiag-build:20261024
FROM ${BASE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git patch && rm -rf /var/lib/apt/lists/*
