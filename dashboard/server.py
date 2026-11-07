"""Refocus project dashboard.

Stdlib only. Run:  python server.py   (127.0.0.1:8791)
Auth: every request needs ?key=<token> (or header X-Key). Token in token.txt.

Endpoints
  GET  /                      dashboard page
  GET  /api/state             status.json + recent metrics + log tails
  GET  /files/<name>          files from D:\Refocus\dashboard\public (report.pdf, samples/*)
  POST /api/ingest/metric     {"run":..., "step":..., "loss":..., ...}  (from Lambda training)
  POST /api/ingest/log        {"run":..., "line":...}
  POST /api/ingest/image      ?name=foo.jpg  body=raw bytes  -> public/samples/
  POST /api/status            replace status.json (used by Claude to update the checklist)
"""
import json, os, secrets, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
os.makedirs(os.path.join(PUBLIC, "samples"), exist_ok=True)
TOKEN_FILE = os.path.join(ROOT, "token.txt")
if not os.path.exists(TOKEN_FILE):
    open(TOKEN_FILE, "w").write(secrets.token_urlsafe(18))
TOKEN = open(TOKEN_FILE).read().strip()

STATUS = os.path.join(ROOT, "status.json")
METRICS = os.path.join(ROOT, "metrics.jsonl")
SYS = os.path.join(ROOT, "sys.jsonl")
LOGS = os.path.join(ROOT, "log.jsonl")
LOCK = threading.Lock()


def tail_jsonl(path, n):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()[-n:]
    out = []
    for l in lines:
        try:
            out.append(json.loads(l))
        except Exception:
            pass
    return out


def metrics_downsampled(maxpts=600):
    if not os.path.exists(METRICS):
        return []
    with open(METRICS, "r", encoding="utf-8") as f:
        rows = [json.loads(l) for l in f if l.strip()]
    if len(rows) > maxpts:
        stride = len(rows) // maxpts + 1
        rows = rows[::stride] + rows[-1:]
    return rows



# ---- photo -> focal stack generation (GPU server reached through an ssh tunnel on 127.0.0.1:8801)
import base64, urllib.request, uuid
GEN_ROOT = os.path.join(ROOT, "gen"); os.makedirs(GEN_ROOT, exist_ok=True)
BACKEND = "http://127.0.0.1:8801"
JOBS = {}
GEN_LOCK = threading.Lock()

def backend_health():
    try:
        return json.load(urllib.request.urlopen(BACKEND + "/health", timeout=3))
    except Exception:
        return None

def run_job(jid, raw, pos):
    j = JOBS[jid]
    try:
        j["state"] = "queued"
        with GEN_LOCK:       # one job at a time; the GPU server also serialises
            j["state"] = "running"; j["t_start"] = time.time()
            req = urllib.request.Request(BACKEND + "/gen?pos=%d" % pos, data=raw, method="POST")
            d = json.load(urllib.request.urlopen(req, timeout=600))
        os.makedirs(os.path.join(GEN_ROOT, jid), exist_ok=True)
        for i, b in enumerate(d["frames"]):
            open(os.path.join(GEN_ROOT, jid, "frame_%d.jpg" % i), "wb").write(base64.b64decode(b))
        j.update(state="done", seconds=d.get("seconds"), size=d.get("size"))
    except Exception as e:
        j.update(state="error", error=str(e)[:200])


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _auth(self):
        q = parse_qs(urlparse(self.path).query)
        k = (q.get("key") or [self.headers.get("X-Key", "")])[0]
        return secrets.compare_digest(k, TOKEN)

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Demo viewer: /v/<token>/<file>  (token in the PATH so the viewer's relative URLs keep working, e.g. on a phone)
        pth = urlparse(self.path).path
        if pth.startswith("/v/"):
            parts = pth[3:].split("/", 1)
            if not secrets.compare_digest(parts[0], TOKEN):
                return self._send(401, {"error": "bad key"})
            rel = (parts[1] if len(parts) > 1 and parts[1] else "index.html").replace("\\", "/")
            if rel == "api/backend":
                return self._send(200, {"online": backend_health() is not None, "info": backend_health()})
            if rel.startswith("api/gen/"):
                j = JOBS.get(rel[8:])
                return self._send(200 if j else 404, dict(j, elapsed=round(time.time() - j["t0"], 1)) if j else {"error": "unknown job"})
            if rel.startswith("gen/"):
                g = os.path.normpath(os.path.join(GEN_ROOT, rel[4:]))
                if not g.startswith(GEN_ROOT) or not os.path.isfile(g):
                    return self._send(404, {"error": "nf"})
                body = open(g, "rb").read()
                self.send_response(200); self.send_header("Content-Type", "image/jpeg"); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "max-age=3600"); self.end_headers(); self.wfile.write(body); return
            vroot = os.path.normpath(os.path.join(ROOT, "..", "viewer"))
            full = os.path.normpath(os.path.join(vroot, rel))
            if not full.startswith(vroot) or not os.path.isfile(full):
                return self._send(404, {"error": "nf"})
            ct = {"html": "text/html; charset=utf-8", "js": "text/javascript; charset=utf-8", "css": "text/css; charset=utf-8", "json": "application/json", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(full.rsplit(".", 1)[-1].lower(), "application/octet-stream")
            body = open(full, "rb").read()
            self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "max-age=300"); self.end_headers(); self.wfile.write(body); return
        if not self._auth():
            return self._send(401, {"error": "bad key"})
        p = urlparse(self.path).path
        if p == "/":
            return self._send(200, open(os.path.join(ROOT, "index.html"), "rb").read(), "text/html; charset=utf-8")
        if p == "/api/state":
            st = json.load(open(STATUS, encoding="utf-8")) if os.path.exists(STATUS) else {}
            return self._send(200, {
                "status": st,
                "metrics": metrics_downsampled(),
                "logs": tail_jsonl(LOGS, 80),
                "sys": tail_jsonl(SYS, 240),
                "cloud": (json.load(open(os.path.join(ROOT, "cloud.json"), encoding="utf-8")) if os.path.exists(os.path.join(ROOT, "cloud.json")) else None),
                "images": sorted(os.listdir(os.path.join(PUBLIC, "samples")))[-24:],
                "files": [f for f in os.listdir(PUBLIC) if os.path.isfile(os.path.join(PUBLIC, f))],
                "now": time.time(),
            })
        if p.startswith("/files/"):
            rel = p[len("/files/"):].replace("\\", "/")
            full = os.path.normpath(os.path.join(PUBLIC, rel))
            if not full.startswith(PUBLIC) or not os.path.isfile(full):
                return self._send(404, {"error": "nf"})
            ct = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                  "gif": "image/gif", "mp4": "video/mp4", "txt": "text/plain; charset=utf-8", "log": "text/plain; charset=utf-8",
                  "yaml": "text/plain; charset=utf-8", "py": "text/plain; charset=utf-8", "tex": "text/plain; charset=utf-8",
                  "md": "text/plain; charset=utf-8", "json": "text/plain; charset=utf-8", "sh": "text/plain; charset=utf-8"}.get(full.rsplit(".", 1)[-1].lower(), "application/octet-stream")
            return self._send(200, open(full, "rb").read(), ct)
        self._send(404, {"error": "nf"})

    def do_POST(self):
        pth = urlparse(self.path)
        if pth.path.startswith("/v/"):
            parts = pth.path[3:].split("/", 1)
            if not secrets.compare_digest(parts[0], TOKEN):
                return self._send(401, {"error": "bad key"})
            if len(parts) > 1 and parts[1] == "api/gen":
                n = int(self.headers.get("Content-Length", 0))
                if n <= 0 or n > 20_000_000:
                    return self._send(400, {"error": "image missing or larger than 20 MB"})
                raw = self.rfile.read(n)
                if backend_health() is None:
                    return self._send(503, {"error": "The GPU server is offline right now."})
                try:
                    pos = int((parse_qs(pth.query).get("pos") or ["4"])[0])
                except ValueError:
                    pos = 4
                jid = uuid.uuid4().hex[:10]
                JOBS[jid] = {"state": "queued", "t0": time.time(), "pos": pos}
                os.makedirs(os.path.join(GEN_ROOT, jid), exist_ok=True); open(os.path.join(GEN_ROOT, jid, "input.bin"), "wb").write(raw)
                threading.Thread(target=run_job, args=(jid, raw, pos), daemon=True).start()
                return self._send(200, {"id": jid})
            return self._send(404, {"error": "nf"})
        if not self._auth():
            return self._send(401, {"error": "bad key"})
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b""
        with LOCK:
            if u.path == "/api/ingest/metric":
                d = json.loads(raw); d["t"] = time.time()
                open(METRICS, "a", encoding="utf-8").write(json.dumps(d) + "\n")
            elif u.path == "/api/ingest/sys":
                d = json.loads(raw); d["t"] = time.time()
                open(SYS, "a", encoding="utf-8").write(json.dumps(d) + "\n")
                lines = open(SYS, encoding="utf-8").read().splitlines()
                if len(lines) > 2000: open(SYS, "w", encoding="utf-8").write("\n".join(lines[-1000:]) + "\n")
            elif u.path == "/api/ingest/cloud":
                d = json.loads(raw); d["t"] = time.time()
                open(os.path.join(ROOT, "cloud.json"), "w", encoding="utf-8").write(json.dumps(d))
            elif u.path == "/api/ingest/log":
                d = json.loads(raw); d["t"] = time.time()
                open(LOGS, "a", encoding="utf-8").write(json.dumps(d) + "\n")
            elif u.path == "/api/ingest/image":
                name = os.path.basename((parse_qs(u.query).get("name") or ["x.jpg"])[0])
                open(os.path.join(PUBLIC, "samples", name), "wb").write(raw)
            elif u.path == "/api/status":
                open(STATUS, "wb").write(raw)
            else:
                return self._send(404, {"error": "nf"})
        self._send(200, {"ok": True})


if __name__ == "__main__":
    print("dashboard on http://127.0.0.1:8791  key in", TOKEN_FILE)
    ThreadingHTTPServer(("127.0.0.1", 8791), H).serve_forever()
