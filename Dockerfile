# syntax=docker/dockerfile:1
# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM rust:1.85-bookworm AS builder

WORKDIR /usr/src/app

COPY Cargo.toml Cargo.lock ./
COPY core_domain core_domain
COPY storage storage
COPY axum_adapter axum_adapter
COPY wasi_adapter wasi_adapter

RUN cargo build --release -p axum_adapter

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
