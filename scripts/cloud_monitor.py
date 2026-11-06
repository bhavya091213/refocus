"""Poll Lambda API + the instance (over SSH) and push a summary to the dashboard every ~20 s.
Reads logs/instance_id.txt, logs/deadline.txt (watchdog), logs/launch.json mtime (billing start).
Job progress: last line of ~/job.log on the instance (symlink/alias to whatever is running) or ~/smoke.log."""
import json, os, subprocess, time, urllib.request, urllib.error

R = "D:/Refocus/"
B = "https://cloud.lambda.com/api/v1"
BUDGET = 100
KEY = open(R + "secrets/lambda.key").read().strip()
DASH = "http://127.0.0.1:8791/api/ingest/cloud?key=" + open(R + "dashboard/token.txt").read().strip()
SSH_KEY = os.path.expanduser("~/.ssh/lambda_parakeet_ed25519")


def api(path):
    req = urllib.request.Request(B + path, headers={"Authorization": "Bearer " + KEY, "User-Agent": "curl/8"})
    return json.load(urllib.request.urlopen(req, timeout=25))


def post(d):
    req = urllib.request.Request(DASH, data=json.dumps(d).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10).read()


def ssh(ip, cmd):
    return subprocess.run(["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8", "-o", "UserKnownHostsFile=NUL",
                           "ubuntu@" + ip, cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30).stdout or ""


GPU_FIELDS = ["index", "name", "uuid", "pci.bus_id", "driver_version", "vbios_version", "persistence_mode", "compute_mode", "pstate", "fan.speed",
              "temperature.gpu", "temperature.memory", "utilization.gpu", "utilization.memory", "memory.total", "memory.used", "memory.free",
              "power.draw", "power.limit", "enforced.power.limit", "power.max_limit", "clocks.sm", "clocks.mem", "clocks.max.sm", "clocks.max.mem",
              "pcie.link.gen.current", "pcie.link.gen.max", "pcie.link.width.current", "pcie.link.width.max", "ecc.mode.current",
              "ecc.errors.corrected.volatile.total", "ecc.errors.uncorrected.volatile.total", "clocks_throttle_reasons.active", "mig.mode.current", "serial"]
REMOTE = ("nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits; echo @@;"
          "pgrep -f 'svd_runner|train|simple_inference' >/dev/null && echo RUNNING || echo IDLE; echo @@;"
          "f=$(ls -t ~/job.log ~/smoke.log ~/train*.log 2>/dev/null | head -1); echo $f; tail -c 700 $f 2>/dev/null | tr '\\r' '\\n' | grep -v '^\\s*$' | tail -3;"
          "echo @@; nvidia-smi --query-gpu=" + ",".join(GPU_FIELDS) + " --format=csv,noheader,nounits;"
          "echo @@; nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv,noheader,nounits;"
          "echo @@; uptime; free -m | sed -n 2p; df -h / | tail -1;"
          "echo @@; for f in $(ls -t ~/train_*.log ~/eval_*.log ~/pipeline.log 2>/dev/null | head -8); do echo \"== $f\"; tail -c 400 $f | tr '\\r' '\\n' | grep -v '^\\s*$' | tail -1; done")
TOPO_CMD = "nvidia-smi topo -m | sed 's/\\x1b\\[[0-9;]*m//g'"
THROTTLE = {0x1: "GPU idle", 0x2: "application clocks setting", 0x4: "SW power cap", 0x8: "HW slowdown", 0x10: "sync boost", 0x20: "SW thermal slowdown",
            0x40: "HW thermal slowdown", 0x80: "HW power brake slowdown", 0x100: "display clocks setting"}
hist = {}      # gpu index -> list of [t, util, mem_used_MiB, temp, power_W]
topo = {"t": 0, "text": ""}

while True:
    out = {"budget": BUDGET, "status": "none", "gpu": {}}
    try:
        iid = open(R + "logs/instance_id.txt").read().strip()
        launched = os.path.getmtime(R + "logs/launch.json")
        try:
            d = api("/instances/" + iid)["data"]
            out.update(status=d["status"], ip=d.get("ip"), type=d["instance_type"]["description"], region=d["region"]["name"],
                       price_hr=d["instance_type"]["price_cents_per_hour"] / 100)
            out["uptime_s"] = time.time() - launched
            out["cost"] = out["uptime_s"] / 3600 * out["price_hr"]
            try:
                out["deadline_in_s"] = int(open(R + "logs/deadline.txt").read()) - time.time()
            except Exception:
                pass
            if d["status"] == "active" and d.get("ip"):
                parts = ssh(d["ip"], REMOTE).split("@@")
                rows = [[x.strip() for x in ln.split(",")] for ln in parts[0].strip().splitlines() if ln.count(",") == 3]
                if rows:
                    out["gpu"] = {"util": round(sum(int(r[0]) for r in rows) / len(rows)), "mem_used": max(int(r[1]) for r in rows),
                                  "mem_total": int(rows[0][2]), "temp": max(int(r[3]) for r in rows), "n": len(rows)}
                out["job_running"] = "RUNNING" in parts[1] if len(parts) > 1 else False
                out["job_tail"] = parts[2].strip() if len(parts) > 2 else ""
                # ---- per-GPU metadata, history, processes, host, per-run log tails
                def num(v):
                    try: return float(v)
                    except Exception: return None
                gpus = []
                if len(parts) > 3:
                    import csv, io
                    for r in csv.reader(io.StringIO(parts[3].strip()), skipinitialspace=True):
                        if len(r) == len(GPU_FIELDS):
                            g = dict(zip(GPU_FIELDS, r))
                            try: mask = int(g["clocks_throttle_reasons.active"], 16)
                            except Exception: mask = 0
                            g["throttle"] = [n for bit, n in THROTTLE.items() if mask & bit] or ["none"]
                            gpus.append(g)
                            i = int(g["index"]); h = hist.setdefault(i, [])
                            h.append([time.time(), num(g["utilization.gpu"]), num(g["memory.used"]), num(g["temperature.gpu"]), num(g["power.draw"])])
                            del h[:-240]
                procs = []
                if len(parts) > 4:
                    for ln in parts[4].strip().splitlines():
                        f = [x.strip() for x in ln.split(",")]
                        if len(f) == 4: procs.append(dict(uuid=f[0], pid=f[1], name=f[2], mem=f[3]))
                out["gpus"] = gpus; out["hist"] = {str(k): v for k, v in hist.items()}; out["procs"] = procs
                out["host"] = parts[5].strip() if len(parts) > 5 else ""
                out["runs"] = parts[6].strip() if len(parts) > 6 else ""
                if time.time() - topo["t"] > 600:
                    topo["text"] = ssh(d["ip"], TOPO_CMD).strip(); topo["t"] = time.time()
                out["topo"] = topo["text"]
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):  # instance no longer exists
                out.update(status="terminated", job_tail="instance no longer exists (terminated)")
                if "cost" not in out:
                    out["cost"] = None
            else:
                raise
        post(out)
    except Exception as e:
        try:
            post({"budget": BUDGET, "status": "monitor error", "gpu": {}, "job_tail": str(e)[:200]})
        except Exception:
            pass
    time.sleep(20)
