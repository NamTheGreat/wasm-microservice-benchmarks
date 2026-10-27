import subprocess
import time
import os

def measure_rss_kb(pid):
    try:
        out = subprocess.check_output(["ps", "-o", "rss=", "-p", str(pid)])
        return int(out.strip())
    except Exception:
        return 0

# 1. Native
p_native = subprocess.Popen(["./target/release/axum_adapter"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
native_idle_rss = measure_rss_kb(p_native.pid)
subprocess.run(["wrk", "-t4", "-c50", "-d5s", "http://127.0.0.1:3000/health"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
native_load_rss = measure_rss_kb(p_native.pid)
p_native.terminate()
p_native.wait()

# 2. Wasmtime AOT
p_wasm = subprocess.Popen(["wasmtime", "serve", "--allow-precompiled", "-S", "cli=y", "--addr", "127.0.0.1:3000", "target/wasi_adapter.cwasm"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
wasm_idle_rss = measure_rss_kb(p_wasm.pid)
subprocess.run(["wrk", "-t4", "-c50", "-d5s", "http://127.0.0.1:3000/health"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
wasm_load_rss = measure_rss_kb(p_wasm.pid)
p_wasm.terminate()
p_wasm.wait()

# 3. Docker (via docker stats snapshot)
p_doc = subprocess.Popen(["docker", "run", "--rm", "--name", "mem_doc", "-p", "3000:3000", "wasm-bench-server:latest"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
try:
    doc_idle = subprocess.check_output(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", "mem_doc"]).decode().strip()
except Exception:
    doc_idle = "N/A"
subprocess.run(["wrk", "-t4", "-c50", "-d5s", "http://127.0.0.1:3000/health"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    doc_load = subprocess.check_output(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", "mem_doc"]).decode().strip()
except Exception:
    doc_load = "N/A"
subprocess.run(["docker", "stop", "mem_doc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print(f"Native RSS:    Idle = {native_idle_rss/1024:.2f} MB, Load = {native_load_rss/1024:.2f} MB")
print(f"Wasmtime RSS:  Idle = {wasm_idle_rss/1024:.2f} MB, Load = {wasm_load_rss/1024:.2f} MB")
print(f"Docker Mem:    Idle = {doc_idle}, Load = {doc_load}")

with open("benchmarks/results/memory_measurements.txt", "w") as f:
    f.write(f"Native: idle={native_idle_rss/1024:.2f}MB, load={native_load_rss/1024:.2f}MB\n")
    f.write(f"Wasmtime: idle={wasm_idle_rss/1024:.2f}MB, load={wasm_load_rss/1024:.2f}MB\n")
    f.write(f"Docker: idle={doc_idle}, load={doc_load}\n")
