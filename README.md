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

## 📖 About the Project

### 🎯 Research Context & Objectives
In modern cloud-native and edge computing architectures, microservices are deployed inside encapsulation boundaries to strike a balance between **security isolation** and **execution performance**. 

This repository provides an empirical testbed comparing three prominent deployment encapsulation paradigms under identical workloads:
1. **Bare-Metal Native Binary:** High-throughput native execution (`aarch64` / `x86_64`) via Tokio & Axum with direct kernel socket management.
2. **OCI Linux Container:** Operating system-level namespace and cgroups virtualization via minimal multi-stage Docker images (tested on Docker Desktop on macOS).
3. **Standalone WebAssembly (WASI Preview 2):** In-process Software-Fault Isolation (SFI) over linear memory via Wasmtime AOT (`.cwasm`).

### ❓ Core Research Questions
* **RQ1 (Cold-Start Overhead):** What is the exact startup latency distribution when instantiating cold microservices across Native, Wasm, and Container runtimes?
* **RQ2 (Steady-State Throughput & Tail Latency):** How do system call virtualization and capability checks in WASI impact $p50$, $p90$, and $p99$ latencies under high concurrency (1, 50, and 200 concurrent connections)?
* **RQ3 (Overhead Mechanisms & Memory):** What architectural mechanisms (per-request instance lifecycles, memory marshalling, runtime engine footprint) govern the steady-state performance differences?

### 🔬 Implementation Notes
* **Core Logic Sharing:** A shared Rust crate (`core_domain`) defines the data structures and Fibonacci compute logic across targets.
* **Storage Consideration:** Native and Docker access a local SQLite database (`rusqlite`) serialized via `std::sync::Mutex`. In the Wasm component (`wasi_adapter`), structured item queries return an in-memory collection due to Wasi C-sysroot requirements. This difference is explicitly disclosed in the methodology.

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
|   +-------------------------------+                             +------------------------------+   |
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
|                                                                                                    |
|   +--------------------------------------------------------------------------------------------+   |
|   |                       benchmarks (Harnesses, Automated Sweeps & Raw Data)                  |   |
|   +--------------------------------------------------------------------------------------------+   |
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
├── core_domain/                # Pure business logic, request types, CPU compute probe
│   └── src/
│       ├── lib.rs              # Re-exports domain types
│       ├── item.rs             # Serde models for Item entities
│       ├── compute.rs          # Iterative Fibonacci probe (std::hint::black_box)
│       └── error.rs            # Domain-level error definitions
├── storage/                    # Relational persistence layer for Native & Docker
│   └── src/
│       ├── lib.rs              # Re-exports StorageBackend
│       ├── backend.rs          # rusqlite wrapper with WAL journal mode
│       └── error.rs            # Storage error handling
├── axum_adapter/               # High-concurrency asynchronous HTTP server
│   └── src/
│       └── main.rs             # Axum 0.8 REST API (benchmarks: /health, /compute/:n, /items + CRUD)
├── wasi_adapter/               # WebAssembly component (wasi:http/incoming-handler)
│   └── src/
│       └── lib.rs              # wasm32-wasip2 component implementation
└── benchmarks/                 # Automated experimental harness & empirical results
    ├── bench_cold_start.rs     # Compiled launch-to-first-byte socket probe
    ├── run_wrk_suite.py        # Automated wrk concurrency sweep harness (1, 50, 200 conns)
    ├── measure_docker_cold.py  # Container startup polling harness (N=30)
    ├── measure_memory.py       # Live RSS and cgroup memory profiler
    ├── analyze_all.py          # Mann-Whitney U & Cliff's delta statistical evaluator
    └── results/                # Raw per-trial output (.txt and .json)
```

---

## 🛠️ Prerequisites & Setup

Ensure the following tools are installed on your system:

| Dependency | Minimum Version | Installation Command |
|---|:---:|---|
| **Rust Toolchain** | `1.85+` | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| **WASI Targets** | `Preview 2` | `rustup target add wasm32-wasip2` |
| **Wasmtime** | `49.0+` | `brew install wasmtime` or `curl https://wasmtime.dev/install.sh \| bash` |
| **wrk** | `4.2+` | `brew install wrk` |
| **Docker** | `24.0+` | [Docker Desktop / Engine](https://docs.docker.com/get-docker/) |
| **Python 3** | `3.10+` | With `numpy` and `scipy` for running statistical analysis |

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
docker build -t wasm-bench-server:latest .

# 3. WebAssembly component (wasm32-wasip2)
cargo +1.85.0 build --manifest-path wasi_adapter/Cargo.toml --target wasm32-wasip2 --release

# 4. Ahead-of-Time (AOT) compile Wasm component
wasmtime compile -O opt-level=2 target/wasm32-wasip2/release/wasi_adapter.wasm -o target/wasi_adapter.cwasm
```

---

## 🌐 Running the Services

### Target 1: Bare-Metal Native
```bash
PORT=3000 TARGET_NAME=native ./target/release/axum_adapter
```

### Target 2: OCI Docker Container
```bash
docker run --rm -p 3000:3000 wasm-bench-server:latest
```

### Target 3: Standalone Wasmtime (AOT Compiled)
```bash
wasmtime serve --allow-precompiled -S cli=y --addr 127.0.0.1:3000 target/wasi_adapter.cwasm
```

---

## 📡 REST API Specification

| Method | Endpoint | Description | Workload Characteristic |
|---|---|---|---|
| `GET` | `/health` | Service status & target identification | Zero-I/O Network Baseline |
| `GET` | `/compute/:n` | Fibonacci($n$) via `std::hint::black_box()` | Minimal Compute Probe ($\approx 1\,\mu\text{s}$ at $n=20$) |
| `GET` | `/items` | List structured records (JSON array) | Structured Object Serialization |

*Note on endpoints:* While `axum_adapter` implements full CRUD handlers (`POST /items`, `GET /items/:id`, `PUT /items/:id`, `DELETE /items/:id`) for microservice realism, the empirical evaluation focuses on `/health`, `/compute/:n`, and `/items` to maintain strict functional equivalence across all three execution targets.

---

## 📊 Empirical Benchmark Results (Apple Silicon M-Series)

All measurements below are collected from the automated test harness (`benchmarks/`) running on macOS ARM64.

### 1. Cold-Start Latency (Process Spawn $\to$ First HTTP 200 OK)
*Measured via compiled socket-polling harness (`bench_cold_start.rs` for Native and Wasm) and container daemon polling (`measure_docker_cold.py` for Docker):*

| Deployment Target | Sample Size ($N$) | Median | IQR | Mean $\pm$ StdDev | Min | Max |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Bare-Metal Native** | 50 | **15.49 ms** | 1.15 ms | $15.88 \pm 4.74\,\text{ms}$ | 8.65 ms | 46.27 ms |
| **Wasmtime AOT (`.cwasm`)** | 50 | **19.28 ms** | 2.90 ms | $19.99 \pm 4.87\,\text{ms}$ | 16.67 ms | 51.14 ms |
| **OCI Docker Container (macOS)** | 30 | **107.39 ms** | 6.34 ms | $106.94 \pm 5.33\,\text{ms}$ | 97.62 ms | 118.85 ms |

*Two-sided Mann-Whitney $U$ test:*  
* Wasm vs. Native: $U = 2406.0, p = 1.64 \times 10^{-15}$, Cliff's Delta $\delta = 0.925$.  
* Docker vs. Wasm: $U = 1500.0, p = 9.43 \times 10^{-14}$, Cliff's Delta $\delta = 1.000$.

*Note on cold starts:* Native and Docker cold-start latencies reflect the auto-seeded storage build (where the backend checks/seeds 10 initial SQLite items on startup before serving requests). Docker measurements utilize `measure_docker_cold.py` polling via `urllib.request` over the Docker daemon lifecycle.

### 2. Steady-State Concurrency Sweep (Throughput & Latency)
*Measured via closed-loop `wrk` across 3 independent trials per configuration (5s warmup, 10s sample):*

| Target | Endpoint | Concurrency | Mean Throughput | Median $p50$ | Median $p90$ | Median $p99$ |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Native** | `/health` | 50 | 139,324 req/s | 225.0 µs | 319.0 µs | 495.0 µs |
| **Native** | `/compute` | 50 | 168,214 req/s | 232.0 µs | 326.0 µs | 443.0 µs |
| **Native** | `/items` | 50 | 92,337 req/s | 515.0 µs | 780.0 µs | 1,060.0 µs |
| **Wasmtime AOT** | `/health` | 50 | 27,191 req/s | 1,750.0 µs | 2,560.0 µs | 3,230.0 µs |
| **Wasmtime AOT** | `/compute` | 50 | 25,092 req/s | 1,900.0 µs | 2,780.0 µs | 3,500.0 µs |
| **Wasmtime AOT** | `/items` | 50 | 25,831 req/s | 1,830.0 µs | 2,700.0 µs | 3,540.0 µs |
| **Docker (macOS)** | `/health` | 50 | 60,839 req/s | 764.0 µs | 1,020.0 µs | 1,420.0 µs |
| **Docker (macOS)** | `/compute` | 50 | 58,710 req/s | 782.0 µs | 1,050.0 µs | 1,470.0 µs |
| **Docker (macOS)** | `/items` | 50 | 36,493 req/s | 1,250.0 µs | 2,000.0 µs | 3,000.0 µs |

### 3. Memory Footprint (RSS) and Artifact Size

| Target | Idle Memory | Under-Load Memory (50 Conn) | Artifact Size | Description |
|---|:---:|:---:|:---:|---|
| **Bare-Metal Native** | 4.02 MB | 8.41 MB | 4.5 MB | Standalone Mach-O binary |
| **Wasmtime AOT** | 8.89 MB | 17.31 MB | 0.43 MB (.cwasm) / 0.16 MB (.wasm) | Pre-compiled component |
| **OCI Docker Container** | ~1.46 MB (cgroup) | ~3.95 MB (cgroup) | 32.1 MB | Debian slim image |

*Note on memory measurements:* Native and Wasmtime figures represent process Resident Set Size (RSS). Docker figures represent internal cgroup accounting (`docker stats`) reported by the Linux container engine, excluding the host hypervisor and Docker Desktop baseline. "Under-Load Memory" is sampled immediately after the sustained 50-connection `wrk` load test concludes on `/health` (quiescent peak footprint).

---

## ⚖️ Architectural Decision Heuristics

* **Deploy WebAssembly When:**
  * **Workloads are ephemeral or bursty:** Wasm's **19.28 ms** cold start eliminates container startup stalls in serverless environments.
  * **Executing untrusted multitenant plugins:** In-process SFI and capability validation provide robust security without virtual machine overhead.
  * **Binary storage constraints are tight:** Compact `.cwasm` artifacts (428 KB) allow efficient distribution to edge nodes.
* **Retain Docker Containers or Native Binaries When:**
  * **Processing sustained high-throughput HTTP traffic:** Direct OS kernel socket handling achieves higher throughput and sub-millisecond tail latencies ($p99 < 500\,\mu\text{s}$).
  * **Requiring raw POSIX / async kernel I/O:** Applications requiring custom socket options or deep kernel features remain best suited for native or container environments.

---

## 🔬 Reproducing the Benchmarks

To run the complete benchmark suite and verify the statistical analysis:

```bash
# 1. Run statistical verification over recorded raw data
python3 benchmarks/analyze_all.py

# 2. Re-run cold start evaluations
rustc -O benchmarks/bench_cold_start.rs -o benchmarks/bench_cold_start
benchmarks/bench_cold_start "./target/release/axum_adapter" 3000 50

# 3. Re-run steady-state concurrency sweep
python3 benchmarks/run_wrk_suite.py native http://127.0.0.1:3000
```

---

## 📖 Citation

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
