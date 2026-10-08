# syntax=docker/dockerfile:1
# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM rust:1.85-bookworm AS builder

WORKDIR /usr/src/app

# Cache dependency fetch separately from source compilation
COPY Cargo.toml Cargo.lock ./
COPY core_domain/Cargo.toml core_domain/Cargo.toml
COPY storage/Cargo.toml     storage/Cargo.toml
COPY axum_adapter/Cargo.toml axum_adapter/Cargo.toml
COPY wasi_adapter/Cargo.toml wasi_adapter/Cargo.toml

# Stub sources so `cargo fetch` / dependency compile step works
RUN mkdir -p core_domain/src storage/src axum_adapter/src wasi_adapter/src \
    && echo "pub fn dummy() {}" > core_domain/src/lib.rs \
    && echo "pub fn dummy() {}" > storage/src/lib.rs \
    && echo "fn main() {}" > axum_adapter/src/main.rs \
    && echo "fn main() {}" > wasi_adapter/src/main.rs \
    && cargo build --release -p axum_adapter 2>/dev/null || true

# Copy real sources and rebuild
COPY core_domain/src/ core_domain/src/
COPY storage/src/      storage/src/
COPY axum_adapter/src/ axum_adapter/src/
COPY wasi_adapter/src/ wasi_adapter/src/

RUN touch axum_adapter/src/main.rs \
    && cargo build --release -p axum_adapter

# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/src/app/target/release/axum_adapter /app/axum_adapter

ENV TARGET_NAME=docker
ENV PORT=3000
EXPOSE 3000

CMD ["/app/axum_adapter"]
