import subprocess
import time
import urllib.request

REPS = 30
results = []

for i in range(1, REPS + 1):
    start = time.perf_counter()
    # Run container with name to easily stop/rm
    cname = f"cold_doc_{i}"
    cmd = ["docker", "run", "-d", "--rm", "--name", cname, "-p", "3002:3000", "wasm-bench-server:latest"]
    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Poll http://127.0.0.1:3002/health
    url = "http://127.0.0.1:3002/health"
    req_success = False
    while time.perf_counter() - start < 15.0:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as resp:
                if resp.status == 200:
                    req_success = True
                    break
        except Exception:
            time.sleep(0.01)
            
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    # Stop container
    subprocess.run(["docker", "stop", cname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if req_success:
        results.append(elapsed_ms)
        print(f"Run {i}: {elapsed_ms:.2f} ms")
    else:
        print(f"Run {i}: TIMEOUT")
    time.sleep(0.1)

with open("benchmarks/results/cold_start_docker.txt", "w") as f:
    for r in results:
        f.write(f"{r:.3f}\n")
