#!/usr/bin/env python3
"""
Automated interleaved cold-start latency benchmark harness.
Executes trials in round-robin interleaved fashion across:
1. Native (Fresh DB: unlinks bench.db before spawn, creates schema and seeds 10 items)
2. Native (Existing DB: opens pre-seeded bench.db from step 1 without seeding)
3. Standalone Wasmtime AOT (.cwasm component)
4. OCI Docker Container (for N=30 rounds)

This eliminates session drift, CPU thermal bias, and ordering artifacts.
"""

import os
import subprocess
import time
import urllib.request
import numpy as np
from scipy import stats

REPS_NATIVE = 50
REPS_WASM = 50
REPS_DOCKER = 30

native_fresh_results = []
native_existing_results = []
wasm_results = []
docker_results = []

print("=" * 70)
print(f"STARTING INTERLEAVED COLD-START BENCHMARK ({REPS_NATIVE} rounds)")
print("=" * 70)

for r in range(1, REPS_NATIVE + 1):
    # 1. Native: Fresh DB (table created + 10 items inserted in single transaction)
    subprocess.run(["rm", "-f", "bench.db", "bench.db-wal", "bench.db-shm"])
    cmd_native = "PORT=3000 TARGET_NAME=native ./target/release/axum_adapter"
    out_fresh = subprocess.check_output(["./target/bench_cold_start", cmd_native, "3000", "1"]).decode().strip()
    nf_ms = float(out_fresh)
    native_fresh_results.append(nf_ms)
    time.sleep(0.05)

    # 2. Native: Existing DB (bench.db already present and populated by step 1)
    out_exist = subprocess.check_output(["./target/bench_cold_start", cmd_native, "3000", "1"]).decode().strip()
    ne_ms = float(out_exist)
    native_existing_results.append(ne_ms)
    time.sleep(0.05)

    # 3. Wasmtime AOT (.cwasm pre-compiled component)
    cmd_wasm = "wasmtime serve --allow-precompiled -S cli=y --addr 127.0.0.1:3000 target/wasi_adapter.cwasm"
    out_wasm = subprocess.check_output(["./target/bench_cold_start", cmd_wasm, "3000", "1"]).decode().strip()
    w_ms = float(out_wasm)
    wasm_results.append(w_ms)
    time.sleep(0.05)

    # 4. OCI Docker Container (rounds 1 to REPS_DOCKER)
    doc_str = "N/A"
    if r <= REPS_DOCKER:
        start = time.perf_counter()
        cname = f"cold_doc_round_{r}"
        cmd_doc = ["docker", "run", "-d", "--rm", "--name", cname, "-p", "3002:3000", "wasm-bench-server:latest"]
        subprocess.run(cmd_doc, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = "http://127.0.0.1:3002/health"
        while time.perf_counter() - start < 15.0:
            try:
                with urllib.request.urlopen(url, timeout=0.5) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.005)
        d_ms = (time.perf_counter() - start) * 1000.0
        subprocess.run(["docker", "stop", cname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        docker_results.append(d_ms)
        doc_str = f"{d_ms:.2f} ms"
        time.sleep(0.05)

    print(f"Round {r:02d}: Native Fresh={nf_ms:6.2f} ms | Native Exist={ne_ms:6.2f} ms | Wasm={w_ms:6.2f} ms | Docker={doc_str}")

# Save raw output files
with open("benchmarks/results/cold_start_native_fresh.txt", "w") as f:
    for x in native_fresh_results:
        f.write(f"{x:.3f}\n")

with open("benchmarks/results/cold_start_native_existing.txt", "w") as f:
    for x in native_existing_results:
        f.write(f"{x:.3f}\n")

with open("benchmarks/results/cold_start_wasmtime.txt", "w") as f:
    for x in wasm_results:
        f.write(f"{x:.3f}\n")

with open("benchmarks/results/cold_start_docker.txt", "w") as f:
    for x in docker_results:
        f.write(f"{x:.3f}\n")

print("\n" + "=" * 70)
print("INTERLEAVED BENCHMARK SUMMARY")
print("=" * 70)

for name, res in [
    ("Native (Fresh DB)", native_fresh_results),
    ("Native (Existing DB)", native_existing_results),
    ("Wasmtime AOT", wasm_results),
    ("Docker (macOS)", docker_results),
]:
    arr = np.array(res)
    q75, q25 = np.percentile(arr, [75, 25])
    print(f"{name:22} | N={len(arr):2} | Median={np.median(arr):.2f} ms | IQR={q75-q25:.2f} ms | Mean={np.mean(arr):.2f} +/- {np.std(arr):.2f} ms | Min={min(arr):.2f} ms | Max={max(arr):.2f} ms")

# Statistical tests
u_wf, p_wf = stats.mannwhitneyu(wasm_results, native_fresh_results, alternative="two-sided")
cd_wf = (2 * u_wf - len(wasm_results) * len(native_fresh_results)) / (len(wasm_results) * len(native_fresh_results))
print(f"\nWasm vs Native (Fresh DB):    U={u_wf:.1f}, p={p_wf:.2e}, Cliff delta={cd_wf:.3f}")

u_we, p_we = stats.mannwhitneyu(wasm_results, native_existing_results, alternative="two-sided")
cd_we = (2 * u_we - len(wasm_results) * len(native_existing_results)) / (len(wasm_results) * len(native_existing_results))
print(f"Wasm vs Native (Existing DB): U={u_we:.1f}, p={p_we:.2e}, Cliff delta={cd_we:.3f}")

u_dw, p_dw = stats.mannwhitneyu(docker_results, wasm_results, alternative="two-sided")
cd_dw = (2 * u_dw - len(docker_results) * len(wasm_results)) / (len(docker_results) * len(wasm_results))
print(f"Docker vs Wasm:               U={u_dw:.1f}, p={p_dw:.2e}, Cliff delta={cd_dw:.3f}")
