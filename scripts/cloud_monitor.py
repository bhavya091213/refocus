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


REMOTE = ("nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits; echo @@;"
          "pgrep -f 'svd_runner|train|simple_inference' >/dev/null && echo RUNNING || echo IDLE; echo @@;"
          "f=$(ls -t ~/job.log ~/smoke.log ~/train*.log 2>/dev/null | head -1); echo $f; tail -c 700 $f 2>/dev/null | tr '\\r' '\\n' | grep -v '^\\s*$' | tail -3")

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
                g = [x.strip() for x in parts[0].strip().split(",")]
                if len(g) == 4:
                    out["gpu"] = {"util": int(g[0]), "mem_used": int(g[1]), "mem_total": int(g[2]), "temp": int(g[3])}
                out["job_running"] = "RUNNING" in parts[1] if len(parts) > 1 else False
                out["job_tail"] = parts[2].strip() if len(parts) > 2 else ""
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
