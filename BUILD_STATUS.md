# Rust Workspace Build Status

**Date**: 2026-10-01  
**Target Platform**: Apple Silicon ARM64 (`aarch64-apple-darwin`, macOS)  
**Rust Toolchain**: rustc 1.85+ (Edition 2024 / 2021)  

---

## 1. Workspace Structure (`code/`)

```
code/
├── Cargo.toml                  # Workspace root (4 members)
├── Cargo.lock
├── Makefile                    # Targets: build-native, build-docker, build-wasm, build-spin
├── Dockerfile                  # Multi-stage Bookworm slim container for axum_adapter
├── spin.toml                   # Spin v2 HTTP trigger manifest pointing to bench.db
├── .cargo/config.toml          # Target runner configurations
├── core_domain/                # Crates:
│   └── src/
│       ├── lib.rs              # Re-exports Item, CreateItemRequest, fibonacci
│       ├── item.rs             # Serde-serializable Item domain models
│       ├── compute.rs          # Iterative Fibonacci with std::hint::black_box()
│       └── error.rs            # Domain errors
├── storage/
│   └── src/
│       ├── lib.rs              # Re-exports StorageBackend, StorageError
│       ├── backend.rs          # SQLite backend via rusqlite with dual WAL / DELETE mode
│       └── error.rs            # Storage error definitions
├── axum_adapter/
│   └── src/
│       └── main.rs             # Axum 0.8 HTTP server (7 REST endpoints + tracing)
└── wasi_adapter/
    └── src/
        └── main.rs             # wasm32-wasip2 stub (Phase 1 verified)
```

---

## 2. Compilation Verification

| Crate | Target | Status | Artifact / Details |
|---|---|:---:|---|
| `core_domain` | Native & WASI | **PASS** | Unit tests passing (`cargo test -p core_domain`) |
| `storage` | Native (WAL) & WASI (DELETE) | **PASS** | `StorageBackend::open(&path, wal)` supports both modes |
| `axum_adapter` | `aarch64-apple-darwin` | **PASS** | Release binary: `target/release/axum_adapter` (4.7 MB) |
| `wasi_adapter` | `wasm32-wasip2` | **PASS (Stub)** | Minimal component entrypoint ready for Phase 2 WIT binding |

---

## 3. End-to-End Live HTTP Smoke Tests

Executed on port 3099 against local SQLite (`bench.db`):

| Endpoint | Method | Expected | Actual Result | Status |
|---|---|---|---|:---:|
| `/health` | GET | `{"status":"ok","target":"native"}` | `{"status":"ok","target":"native"}` | **PASS** |
| `/compute/10` | GET | `fib(10) = 55` | `{"input":10,"result":55,"elapsed_us":0}` | **PASS** |
| `/items` | POST | 201 Created + Item JSON | `{"id":1,"name":"test_item","value":99.5,...}` | **PASS** |
| `/items` | GET | 200 OK + Array of Items | `[{"id":1,"name":"test_item","value":99.5,...}]` | **PASS** |

---

## 4. Key Architectural Controls Implemented

1. **`std::hint::black_box` in `core_domain::compute::fibonacci`**: Wraps accumulator state on every iteration to guarantee LLVM `-O3` cannot constant-fold recursive/iterative CPU probes away.
2. **Dual Journal Mode in `storage::StorageBackend`**:
   - `wal = true`: Emits `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;` for Native and Docker targets.
   - `wal = false`: Leaves default rollback journal (`DELETE` mode) for WASI Preview 2 targets where POSIX shared memory (`mmap`/`shm`) is unavailable.
3. **Target Identification in `/health`**: `axum_adapter` reads `TARGET_NAME` from environment variables, allowing the automated load harness to verify which encapsulation boundary is actively serving requests.

---

## 5. Next Phase: Benchmarking Harness Execution

1. Build minimal Docker container: `make build-docker` (or `docker build -t wasm-bench-server:latest .`).
2. Implement Phase 2 WIT bindings in `wasi_adapter` targeting `wasi:http/incoming-handler`.
3. Run `benchmark.sh` across targets to collect cold-start and steady-state latency distributions.
