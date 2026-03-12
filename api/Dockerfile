# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies + kubectl + helm for fleet management
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl \
    && curl -fsSL https://get.helm.sh/helm-v3.17.2-linux-amd64.tar.gz | tar xz \
    && install -o root -g root -m 0755 linux-amd64/helm /usr/local/bin/helm \
    && rm -rf linux-amd64 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency installation
RUN pip install uv

# Copy project files
COPY pyproject.toml README.md ./
COPY bootnode/ bootnode/

# Install dependencies
# Hanzo SDKs are optional - in K8s, the KMS operator injects secrets as env vars
RUN uv pip install --system -e .

# Run the application (8000=HTTP API, 9999=ZAP Cap'n Proto RPC)
EXPOSE 8000 9999
CMD ["uvicorn", "bootnode.main:app", "--host", "0.0.0.0", "--port", "8000"]
