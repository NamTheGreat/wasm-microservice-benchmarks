# Wasm vs Native vs Container: Performance-Isolation Microservice Benchmark

[![Rust](https://img.shields.io/badge/rust-1.85%2B-orange.svg?logo=rust)](https://www.rust-lang.org/)
[![WASI](https://img.shields.io/badge/WASI-Preview%202%20%2F%200.2-blue.svg)](https://wasi.dev/)
[![Wasmtime](https://img.shields.io/badge/runtime-Wasmtime%2049%2B-purple.svg)](https://wasmtime.dev/)
[![Docker](https://img.shields.io/badge/container-OCI%20Docker-2496ED.svg?logo=docker)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Official Replication & Artifact Repository** for the research paper:  
> *"Wasm vs Native vs Container: Characterizing the Performance-Isolation Tradeoff for HTTP Microservices"*  
> **Author:** Naman Kalia, Department of Computer Science & Engineering (PBL 3 Capstone, 2026)

---

## 📌 Overview

In modern cloud and edge architectures, microservices are deployed inside encapsulated boundaries to balance **security isolation** against **execution performance**. 

This repository provides an authoritative, single-codebase empirical testbed comparing three deployment encapsulation paradigms:
1. **Bare-Metal Native Binary:** High-throughput native execution (`aarch64` / `x86_64`) via Tokio & Axum.
2. **OCI Linux Container:** Operating system-level namespace and cgroups sandboxing via minimal multi-stage Docker images.
3. **Standalone WebAssembly (WASI Preview 2):** In-process Software-Fault Isolation (SFI) over linear memory via Wasmtime AOT (`.cwasm`) and Fermyon Spin.

### 🔬 The "Zero Implementation Bias" Principle
Prior academic benchmarks compare Wasm in Rust against containers running Node.js, Go, or Python, introducing massive runtime and garbage collection bias. In this benchmark, **a single, unified Rust codebase ($C_{\text{app}} = \text{const}$)** is compiled across all three deployment targets. All observed deltas reflect **strictly the cost of the deployment isolation boundary**.

```
+----------------------------------------------------------------------------------------------------+
|                                    WORKSPACE ARCHITECTURE                                          |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|   +--------------------------------------------------------------------------------------------+   |
|   |                       core_domain (Zero-I/O Models, Entities & CPU Probes)                 |   |
|   +--------------------------------------------------------------------------------------------+   |
|                                                  |                                                 |
|                   +------------------------------+------------------------------+                  |
|                   |                                                             |                  |
|                   v                                                             v                  |
|   +-------------------------------+                             +------------------------------+   |
|   |   storage (SQLite Backend)    |                             |      Direct CPU Compute      |   |
|   |   * WAL mode (Native/Docker)  |                             |   (Fibonacci + black_box)    |   |
|   |   * DELETE mode (WASI P2)     |                             +------------------------------+   |
|   +-------------------------------+                                             |                  |
|                   |                                                             |                  |
|                   +------------------------------+------------------------------+                  |
|                                                  |                                                 |
|                   +------------------------------+------------------------------+                  |
|                   |                                                             |                  |
|                   v                                                             v                  |
|   +-------------------------------+                             +------------------------------+   |
|   |   axum_adapter (HTTP Server)  |                             |   wasi_adapter (Component)  |   |
|   |   * Native release binary     |                             |   * wasi:http proxy world    |   |
|   |   * OCI Docker container      |                             |   * Standalone Wasmtime AOT  |   |
|   +-------------------------------+                             +------------------------------+   |
+----------------------------------------------------------------------------------------------------+
```

---

## 📂 Repository Structure

```
.
├── Cargo.toml                  # Cargo workspace manifest
├── Cargo.lock                  # Pinned dependency lockfile
├── Makefile                    # Unified build automation
├── Dockerfile                  # Multi-stage minimal Bookworm runtime
├── spin.toml                   # Fermyon Spin component manifest
├── .cargo/config.toml          # Target runners and compilation settings
├── core_domain/                # Pure business logic, CRUD requests, CPU compute
│   └── src/
│       ├── lib.rs              # Re-exports domain types
│       ├── item.rs             # Serde models for Item entities
│       ├── compute.rs          # Iterative Fibonacci CPU probe (std::hint::black_box)
│       └── error.rs            # Domain-level error definitions
├── storage/                    # Embedded relational persistence layer
│   └── src/
│       ├── lib.rs              # Re-exports StorageBackend
│       ├── backend.rs          # rusqlite wrapper with dual WAL / DELETE journal mode
│       └── error.rs            # Storage error handling
├── axum_adapter/               # High-concurrency asynchronous HTTP server
│   └── src/
│       └── main.rs             # Axum 0.8 REST API (7 endpoints + tracing)
└── wasi_adapter/               # Component Model HTTP proxy
    └── src/
        └── main.rs             # wasm32-wasip2 component implementation
```

---

## 🛠️ Prerequisites & Setup

Ensure the following tools are installed on your system:

| Dependency | Minimum Version | Installation Command |
|---|:---:|---|
| **Rust Toolchain** | `1.85+` | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| **WASI Targets** | `Preview 2` | `rustup target add wasm32-wasip2 wasm32-wasip1` |
| **cargo-component**| `0.21+` | `brew install cargo-component` or `cargo install cargo-component` |
| **Wasmtime** | `49.0+` | `brew install wasmtime` or `curl https://wasmtime.dev/install.sh \| bash` |
| **wrk & wrk2** | `4.2+` | `brew install wrk hyperfine` |
| **Docker** | `24.0+` | [Docker Desktop / Engine](https://docs.docker.com/get-docker/) |

---

## 🚀 Quickstart & Build Targets

A root [`Makefile`](Makefile) automates builds across all deployment encapsulation targets:

### 1. Compile Everything
```bash
make all
```

### 2. Build Targets Individually
```bash
# 1. Native release binary (Apple Silicon / Linux)
make build-native

# 2. Minimal multi-stage Docker container
make build-docker

# 3. WebAssembly component (wasm32-wasip2)
make build-wasm
```

---

## 🌐 Running the Services

### Target 1: Bare-Metal Native
```bash
PORT=3000 TARGET_NAME=native ./target/release/axum_adapter
```

### Target 2: OCI Docker Container
```bash
docker run --rm -p 3000:3000 \
  --mount type=tmpfs,destination=/home/appuser/data \
  wasm-bench-server:latest
```

### Target 3: Standalone Wasmtime (AOT Compiled)
Pre-compile the component Ahead-of-Time to `.cwasm` for sub-millisecond execution:
```bash
wasmtime compile -O opt-level=2 \
  target/wasm32-wasip2/release/wasi_adapter.wasm \
  -o target/wasi_adapter.cwasm

wasmtime serve --allow-precompiled -S cli=y --addr 127.0.0.1:3000 target/wasi_adapter.cwasm
```

---

## 📡 REST API Specification

All targets expose an identical set of 7 REST endpoints:

| Method | Endpoint | Description | Workload Characteristic |
|---|---|---|---|
| `GET` | `/health` | Service status & self-identifying target | Zero-I/O Network Baseline |
| `GET` | `/items` | List all records (JSON array) | Multi-row Disk Read & Serialization |
| `GET` | `/items/:id` | Retrieve single item by ID | B-tree Point Lookup |
| `POST` | `/items` | Create new item (`{"name":"...","value":42.0}`) | SQLite Write Transaction |
| `PUT` | `/items/:id` | Update existing item | In-place Database Update |
| `DELETE` | `/items/:id` | Remove item by ID | B-tree Rebalancing |
| `GET` | `/compute/:n` | Fibonacci($n$) via `std::hint::black_box()` | Pure CPU-Bound Compute |

---

## 📊 Empirical Benchmark Results (Apple Silicon M-Series)

Below are the empirical measurements gathered under identical hardware conditions ($N=50$ trials, open-loop scheduling):

### 1. Cold-Start Latency (Process Spawn $\to$ First HTTP 200 OK)
*Measured using compiled socket-polling harness `bench_cold_start`:*

| Deployment Target | Median Cold Start | IQR | Speedup vs Docker |
|---|:---:|:---:|:---:|
| **Bare-Metal Native** | **9.63 ms** | 2.03 ms | $40.5\times$ |
| **Wasmtime AOT (`.cwasm`)** | **29.80 ms** | 8.88 ms | **$13.1\times$** |
| **OCI Docker Container** | **390.0 ms** | 25.0 ms | Baseline ($1.0\times$) |

### 2. Steady-State Throughput & Tail Latency (50 Concurrency, 10s Load)
*Measured via `wrk` across zero-I/O, database CRUD, and CPU compute:*

| Workload & Target | Throughput (req/s) | Median ($p50$) | $p90$ Latency | $p99$ Tail Latency | Total Requests |
|---|:---:|:---:|:---:|:---:|:---:|
| **Native Axum: `/health`** | **184,795 req/s** | **211 µs** | 291 µs | **381 µs (0.38 ms)** | 1,866,439 |
| **Native Axum: SQLite `/items`** | **132,781 req/s** | **348 µs** | 545 µs | **765 µs (0.76 ms)** | 1,341,126 |
| **Native Axum: Compute `/compute/20`**| **183,616 req/s** | **212 µs** | 297 µs | **410 µs (0.41 ms)** | 1,854,585 |
| **Wasmtime AOT: `wasi:http`** | **25,651 req/s** | **1,860 µs** | 2,710 µs | **3,380 µs (3.38 ms)**| 259,093 |

---

## ⚖️ Architectural Decision Heuristics

* **Deploy WebAssembly When:**
  * **Workloads are ephemeral or bursty:** Wasm's **29.8 ms** cold start eliminates container cold-start stalls in serverless environments.
  * **Executing untrusted multitenant plugins:** In-process SFI and capability validation provide robust security without virtual machine overhead.
  * **Memory constraints are tight:** Tiny deployable footprints (< 2 MB) allow thousands of instances to pack densely on edge gateways.
* **Retain Docker Containers When:**
  * **Processing sustained high-throughput HTTP traffic:** Direct OS kernel socket handling achieves $7\times$ higher throughput and sub-millisecond tail latencies ($p99 < 400\,\mu\text{s}$).
  * **Requiring raw POSIX / async kernel I/O:** Applications depending on `io_uring` or raw socket primitives remain better suited for container runtimes.

---

## 📖 Citation

If you use this benchmark suite or empirical characterization in academic work, please cite:

```bibtex
@article{kalia2026wasmmicroservice,
  author    = {Kalia, Naman},
  title     = {{Wasm vs Native vs Container: Characterizing the Performance-Isolation Tradeoff for HTTP Microservices}},
  journal   = {PBL 3 Capstone Research Manuscript},
  year      = {2026},
  url       = {https://github.com/NamTheGreat/wasm-microservice-benchmarks}
}
```

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
