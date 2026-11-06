"""Terminate the Lambda instance when now > logs/deadline.txt (epoch). Extend by rewriting that file. Cost safety."""
import json, time, urllib.request
R = "D:/Refocus/"; B = "https://cloud.lambda.com/api/v1"
key = open(R + "secrets/lambda.key").read().strip(); iid = open(R + "logs/instance_id.txt").read().strip()
def call(path, body=None):
    req = urllib.request.Request(B + path, data=json.dumps(body).encode() if body else None, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "curl/8"})
    return json.load(urllib.request.urlopen(req, timeout=30))
while True:
    try:
        dl = int(open(R + "logs/deadline.txt").read())
        if time.time() > dl:
            print(time.ctime(), "DEADLINE -> terminating", iid, call("/instance-operations/terminate", {"instance_ids": [iid]}), flush=True); break
        d = call("/instances/" + iid)["data"]
        if d.get("status") == "terminated": print("instance gone, exiting", flush=True); break
    except Exception as e:
        print(time.ctime(), "err", str(e)[:100], flush=True)
    time.sleep(60)
