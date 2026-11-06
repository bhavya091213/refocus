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
