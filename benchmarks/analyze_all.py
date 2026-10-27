import json
import numpy as np
from scipy import stats

print("="*70)
print("1. COLD-START STATISTICAL SUMMARY")
print("="*70)
c_native = np.loadtxt("benchmarks/results/cold_start_native.txt")
c_wasm = np.loadtxt("benchmarks/results/cold_start_wasmtime.txt")
c_docker = np.loadtxt("benchmarks/results/cold_start_docker.txt")

for name, d in [("Native", c_native), ("Wasmtime AOT", c_wasm), ("Docker (macOS)", c_docker)]:
    q25, q75 = np.percentile(d, [25, 75])
    print(f"{name:15} | N={len(d):2} | Median={np.median(d):.2f} ms | IQR={q75-q25:.2f} ms | Mean={np.mean(d):.2f} ms (std={np.std(d, ddof=1):.2f}) | Min={np.min(d):.2f} ms | Max={np.max(d):.2f} ms")

u_stat, p_val = stats.mannwhitneyu(c_wasm, c_native, alternative="two-sided")
n1, n2 = len(c_wasm), len(c_native)
cd = (2 * u_stat - n1 * n2) / (n1 * n2)
print(f"\nWasm vs Native Mann-Whitney U: U={u_stat:.1f}, p={p_val:.2e}, Cliff delta={cd:.3f}")

u_stat2, p_val2 = stats.mannwhitneyu(c_docker, c_wasm, alternative="two-sided")
n1, n2 = len(c_docker), len(c_wasm)
cd2 = (2 * u_stat2 - n1 * n2) / (n1 * n2)
print(f"Docker vs Wasm Mann-Whitney U: U={u_stat2:.1f}, p={p_val2:.2e}, Cliff delta={cd2:.3f}")

print("\n" + "="*70)
print("2. STEADY-STATE THROUGHPUT & TAIL LATENCY SUMMARY")
print("="*70)
for target in ["native", "wasmtime", "docker"]:
    with open(f"benchmarks/results/wrk_{target}.json") as f:
        data = json.load(f)
    print(f"\n--- TARGET: {target.upper()} ---")
    print(f"{'Endpoint':10} | {'Conn':4} | {'Mean RPS':12} | {'p50 (us)':10} | {'p90 (us)':10} | {'p99 (us)':10}")
    print("-" * 65)
    for r in data:
        print(f"{r['endpoint']:10} | {r['concurrency']:4} | {r['mean_rps']:12.1f} | {r['median_p50_us']:10.1f} | {r['median_p90_us']:10.1f} | {r['median_p99_us']:10.1f}")
