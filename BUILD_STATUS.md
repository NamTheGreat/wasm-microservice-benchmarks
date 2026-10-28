# Rust Workspace Build Status

**Date**: 2026-10-28  
**Target Platform**: Apple Silicon ARM64 (`aarch64-apple-darwin`, macOS)  
**Rust Toolchain**: rustc 1.85+ (Edition 2021)  

---

## 1. Workspace Structure (`code/`)

```
code/
├── Cargo.toml                  # Workspace root (4 members)
├── Cargo.lock
├── Makefile                    # Targets: build-native, build-docker, build-wasm
├── Dockerfile                  # Multi-stage Bookworm slim container for axum_adapter
├── .cargo/config.toml          # Target runner configurations
├── core_domain/                # Crates:
│   └── src/
│       ├── lib.rs              # Re-exports Item, CreateItemRequest, fibonacci
│       ├── item.rs             # Serde-serializable Item domain models
│       ├── compute.rs          # Iterative Fibonacci probe with std::hint::black_box()
│       └── error.rs            # Domain errors
├── storage/
│   └── src/
│       ├── lib.rs              # Re-exports StorageBackend, StorageError
│       ├── backend.rs          # SQLite backend via rusqlite with dual WAL / DELETE mode
│       └── error.rs            # Storage error definitions
├── axum_adapter/
│   └── src/
│       └── main.rs             # Axum 0.8 HTTP server (benchmarks: /health, /compute/:n, /items + CRUD)
├── wasi_adapter/
│   └── src/
│       └── lib.rs              # wasm32-wasip2 component exporting wasi:http/incoming-handler
└── benchmarks/                 # Automated experimental harness & empirical results
    ├── bench_cold_start.rs     # Compiled launch-to-first-byte socket probe
    ├── run_wrk_suite.py        # Automated wrk concurrency sweep harness (1, 50, 200 conns)
    ├── measure_docker_cold.py  # Container startup polling harness (N=30)
    ├── measure_memory.py       # Live RSS and cgroup memory profiler
    ├── analyze_all.py          # Mann-Whitney U & Cliff's delta statistical evaluator
    └── results/                # Raw trial data (.txt and .json)
```

---

## 2. Compilation Verification

| Crate | Target | Status | Artifact / Details |
|---|---|:---:|---|
| `core_domain` | Native & WASI | **PASS** | Unit tests passing (`cargo test -p core_domain`) |
| `storage` | Native (WAL) & WASI (DELETE) | **PASS** | `StorageBackend::open(&path, wal)` supports both modes |
| `axum_adapter` | `aarch64-apple-darwin` | **PASS** | Release binary: `target/release/axum_adapter` (4.5 MB) |
| `wasi_adapter` | `wasm32-wasip2` | **PASS** | Wasm component: `target/wasm32-wasip2/release/wasi_adapter.wasm` (163 KB) |
| `wasi_adapter (AOT)`| Cranelift AOT | **PASS** | AOT pre-compiled component: `target/wasi_adapter.cwasm` (428 KB) |
| Docker Image | OCI Linux ARM64 | **PASS** | Container image: `wasm-bench-server:latest` (32.1 MB) |

---

## 3. End-to-End Live HTTP Smoke Tests

Executed against local daemon instances:

| Endpoint | Method | Native Result | Wasmtime Result | Docker Result | Status |
|---|---|---|---|---|:---:|
| `/health` | GET | `{"status":"ok","target":"native"}` | `{"status":"ok","target":"wasmtime"}` | `{"status":"ok","target":"docker"}` | **PASS** |
| `/compute/20` | GET | `{"input":20,"result":6765,...}` | `{"input":20,"result":6765,...}` | `{"input":20,"result":6765,...}` | **PASS** |
| `/items` | GET | Array of structured items | Array of structured items | Array of structured items | **PASS** |
