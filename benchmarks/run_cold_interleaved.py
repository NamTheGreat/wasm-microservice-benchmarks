#!/usr/bin/env python3
"""
Automated randomized-order interleaved cold-start latency benchmark harness.
Executes trials across all 4 targets in randomized order per round (N=50 rounds):
1. Native (Fresh DB: unlinks bench_fresh.db before spawn, creates schema and seeds 10 items)
2. Native (Existing DB: opens pre-seeded, cleanly checkpointed bench_seeded.db without re-seeding)
3. Standalone Wasmtime AOT (.cwasm component)
4. OCI Docker Container (N=50 rounds, with container teardown settling)

Randomizing the execution order in every round and interleaving all four targets
significantly reduces session drift, CPU thermal bias, and ordering artifacts.
"""

import os
import random
import subprocess
import time
import urllib.request
import numpy as np
from scipy import stats

REPS = 50

native_fresh_results = []
native_existing_results = []
wasm_results = []
docker_results = []

# Pre-seed and cleanly checkpoint bench_seeded.db for Existing DB runs
print("=" * 70)
print("INITIALIZING PRE-SEEDED DATABASE FOR EXISTING DB RUNS")
print("=" * 70)
subprocess.run(["rm", "-f", "bench_seeded.db", "bench_seeded.db-wal", "bench_seeded.db-shm"])
cmd_init = "PORT=3000 DB_PATH=bench_seeded.db TARGET_NAME=native ./target/release/axum_adapter"
subprocess.check_output(["./target/bench_cold_start", cmd_init, "3000", "1"])
subprocess.run(["sqlite3", "bench_seeded.db", "PRAGMA wal_checkpoint(TRUNCATE);"], check=True)
print("bench_seeded.db initialized, 10 items seeded, and WAL cleanly checkpointed.\n")

def run_native_fresh():
    subprocess.run(["rm", "-f", "bench_fresh.db", "bench_fresh.db-wal", "bench_fresh.db-shm"])
    cmd = "PORT=3000 DB_PATH=bench_fresh.db TARGET_NAME=native ./target/release/axum_adapter"
    out = subprocess.check_output(["./target/bench_cold_start", cmd, "3000", "1"]).decode().strip()
    return float(out)

def run_native_existing():
    cmd = "PORT=3000 DB_PATH=bench_seeded.db TARGET_NAME=native ./target/release/axum_adapter"
    out = subprocess.check_output(["./target/bench_cold_start", cmd, "3000", "1"]).decode().strip()
    return float(out)

def run_wasm():
    cmd = "wasmtime serve --allow-precompiled -S cli=y --addr 127.0.0.1:3000 target/wasi_adapter.cwasm"
    out = subprocess.check_output(["./target/bench_cold_start", cmd, "3000", "1"]).decode().strip()
    return float(out)

def run_docker(round_idx):
    start = time.perf_counter()
    cname = f"cold_doc_rnd_{round_idx}_{random.randint(1000, 9999)}"
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
    time.sleep(0.15)  # Allow container subsystem to settle
    return d_ms

print("=" * 70)
print(f"STARTING RANDOMIZED-ORDER INTERLEAVED BENCHMARK ({REPS} rounds)")
print("=" * 70)

for r in range(1, REPS + 1):
    # Prepare targets and shuffle order for this round
    targets = [
        ("native_fresh", run_native_fresh),
        ("native_existing", run_native_existing),
        ("wasm", run_wasm),
        ("docker", lambda r=r: run_docker(r)),
    ]
    random.shuffle(targets)
    round_order = [t[0] for t in targets]

    round_timings = {}
    for name, fn in targets:
        val = fn()
        round_timings[name] = val
        time.sleep(0.05)

    native_fresh_results.append(round_timings["native_fresh"])
    native_existing_results.append(round_timings["native_existing"])
    wasm_results.append(round_timings["wasm"])
    docker_results.append(round_timings["docker"])

    print(f"Round {r:02d} [{','.join([o[:4] for o in round_order])}]: Fresh={round_timings['native_fresh']:5.2f}ms | Exist={round_timings['native_existing']:5.2f}ms | Wasm={round_timings['wasm']:5.2f}ms | Docker={round_timings['docker']:6.2f}ms")

# Clean up temp test DBs
subprocess.run(["rm", "-f", "bench_fresh.db*", "bench_seeded.db*"])

# Save raw output files
os.makedirs("benchmarks/results", exist_ok=True)
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
print("INTERLEAVED BENCHMARK SUMMARY (N=50 ALL TARGETS)")
print("=" * 70)

for name, res in [
    ("Native (Fresh DB)", native_fresh_results),
    ("Native (Existing DB)", native_existing_results),
    ("Wasmtime AOT", wasm_results),
    ("Docker (macOS)", docker_results),
]:
    arr = np.array(res)
    q75, q25 = np.percentile(arr, [75, 25])
    print(f"{name:22} | N={len(arr):2} | Median={np.median(arr):.2f} ms | IQR={q75-q25:.2f} ms | Mean={np.mean(arr):.2f} +/- {np.std(arr, ddof=1):.2f} ms | Min={min(arr):.2f} ms | Max={max(arr):.2f} ms")

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
