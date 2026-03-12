# Multi-stage build for bootnode-operator
# Stage 1: Build the Rust binary
FROM rust:1.88-bookworm AS builder

RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Limit parallelism to reduce memory usage
ENV CARGO_BUILD_JOBS=2

# Copy manifest first for dependency caching
COPY Cargo.toml Cargo.lock ./

# Create dummy source for dependency caching
RUN mkdir -p src/drivers && \
    echo "fn main() {}" > src/main.rs

# Build dependencies only (cached layer)
RUN cargo build --release 2>/dev/null || true

# Copy actual source code
COPY src/ src/

# Touch to invalidate cache
RUN touch src/main.rs

# Build the operator
RUN cargo build --release

# Stage 2: Minimal runtime image
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -f bootnode && useradd -r -s /bin/false -g bootnode bootnode

COPY --from=builder /build/target/release/bootnode-operator /usr/local/bin/bootnode-operator
RUN chmod +x /usr/local/bin/bootnode-operator

USER bootnode

EXPOSE 8080 8081

ENTRYPOINT ["/usr/local/bin/bootnode-operator"]
