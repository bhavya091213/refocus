"""Terminate the Lambda instance when now > logs/infer_deadline.txt (epoch). Extend by rewriting that file. Cost safety."""
import json, os, time, urllib.request
R = "D:/Refocus/"; B = "https://cloud.lambda.com/api/v1"
key = open(R + "secrets/lambda.key").read().strip(); iid = open(R + "logs/infer_instance_id.txt").read().strip()
def call(path, body=None):
    req = urllib.request.Request(B + path, data=json.dumps(body).encode() if body else None, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "curl/8"})
    return json.load(urllib.request.urlopen(req, timeout=30))
while True:
    try:
        dl = int(open(R + "logs/infer_deadline.txt").read())
        try: cap = float(open(R + "logs/infer_cost_cap.txt").read())          # hard $ cap for THIS instance's spend (default 75)
        except Exception: cap = 10.0
        try: price = float(open(R + "logs/infer_price_hr.txt").read())
        except Exception: price = 1.29
        cost = (time.time() - os.path.getmtime(R + "logs/launch_infer.json")) / 3600 * price
        if time.time() > dl or cost > cap:
            why = "DEADLINE" if time.time() > dl else f"COST CAP ${cap:.0f} (spent ~${cost:.2f})"
            print(time.ctime(), why, "-> terminating", iid, call("/instance-operations/terminate", {"instance_ids": [iid]}), flush=True); break
        d = call("/instances/" + iid)["data"]
        if d.get("status") == "terminated": print("instance gone, exiting", flush=True); break
    except Exception as e:
        print(time.ctime(), "err", str(e)[:100], flush=True)
    time.sleep(60)
