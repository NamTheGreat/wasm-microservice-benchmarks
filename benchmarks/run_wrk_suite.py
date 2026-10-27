import subprocess
import time
import re
import json
import os

ENDPOINTS = [
    ("/health", "health"),
    ("/compute/20", "compute"),
    ("/items", "items")
]

CONCURRENCY_LEVELS = [1, 50, 200]
TRIALS = 3
WARMUP_SEC = 5
DURATION_SEC = 10

def parse_wrk_output(output):
    res = {}
    
    # Latency distribution
    # Latency   211.23us  120.45us   1.23ms   89.12%
    # Latency Distribution
    #   50%  211.00us
    #   75%  ...
    #   90%  ...
    #   99%  ...
    lat_match = re.search(r"Latency\s+([\d\.]+\w+)\s+([\d\.]+\w+)\s+([\d\.]+\w+)", output)
    if lat_match:
        res["lat_avg"] = lat_match.group(1)
        res["lat_stdev"] = lat_match.group(2)
        res["lat_max"] = lat_match.group(3)
    
    req_match = re.search(r"Requests/sec:\s+([\d\.]+)", output)
    if req_match:
        res["rps"] = float(req_match.group(1))
    
    tot_match = re.search(r"(\d+)\s+requests in", output)
    if tot_match:
        res["total_requests"] = int(tot_match.group(1))
        
    for p in ["50%", "75%", "90%", "99%", "99.9%"]:
        p_esc = p.replace(".", r"\.")
        m = re.search(rf"\s+{p_esc}\s+([\d\.]+\w+)", output)
        if m:
            res[f"p{p[:-1]}"] = m.group(1)
            
    return res

def to_micros(val_str):
    if not val_str:
        return 0.0
    val_str = val_str.strip()
    if val_str.endswith("us") or val_str.endswith("µs"):
        return float(val_str[:-2])
    elif val_str.endswith("ms"):
        return float(val_str[:-2]) * 1000.0
    elif val_str.endswith("s"):
        return float(val_str[:-1]) * 1000000.0
    return float(val_str)

def run_suite(target_name, base_url):
    results = []
    for ep_path, ep_label in ENDPOINTS:
        url = f"{base_url}{ep_path}"
        for c in CONCURRENCY_LEVELS:
            threads = min(c, 4)
            print(f"[{target_name}] Endpoint: {ep_label}, Connections: {c}, Threads: {threads}")
            
            # Warmup
            subprocess.run(["wrk", f"-t{threads}", f"-c{c}", f"-d{WARMUP_SEC}s", url],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            
            trial_data = []
            for t in range(TRIALS):
                p = subprocess.run(["wrk", f"-t{threads}", f"-c{c}", f"-d{DURATION_SEC}s", "--latency", url],
                                   capture_output=True, text=True)
                parsed = parse_wrk_output(p.stdout)
                parsed["trial"] = t + 1
                trial_data.append(parsed)
                time.sleep(1)
                
            # Aggregate over trials
            rpss = [td.get("rps", 0.0) for td in trial_data]
            p50s = [to_micros(td.get("p50", "0us")) for td in trial_data]
            p90s = [to_micros(td.get("p90", "0us")) for td in trial_data]
            p99s = [to_micros(td.get("p99", "0us")) for td in trial_data]
            
            agg = {
                "target": target_name,
                "endpoint": ep_label,
                "concurrency": c,
                "threads": threads,
                "mean_rps": sum(rpss) / len(rpss) if rpss else 0.0,
                "median_p50_us": sorted(p50s)[len(p50s)//2] if p50s else 0.0,
                "median_p90_us": sorted(p90s)[len(p90s)//2] if p90s else 0.0,
                "median_p99_us": sorted(p99s)[len(p99s)//2] if p99s else 0.0,
                "trials": trial_data
            }
            results.append(agg)
            print(f"  -> Mean RPS: {agg['mean_rps']:.1f}, p50: {agg['median_p50_us']:.1f}µs, p99: {agg['median_p99_us']:.1f}µs")
            
    with open(f"benchmarks/results/wrk_{target_name}.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    import sys
    run_suite(sys.argv[1], sys.argv[2])
