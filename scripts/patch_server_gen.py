import io
p = "D:/Refocus/dashboard/server.py"
s = io.open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"; s = s.replace("\r\n", "\n")
assert "GEN_ROOT" not in s
# --- helpers
helpers = '''
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

'''
s = s.replace("class H(BaseHTTPRequestHandler):", helpers + "\nclass H(BaseHTTPRequestHandler):", 1)
# --- GET routes inside the /v/ branch
old = '            rel = (parts[1] if len(parts) > 1 and parts[1] else "index.html").replace("\\\\", "/")\n'
assert old in s
new = old + '''            if rel == "api/backend":
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
'''
s = s.replace(old, new, 1)
# --- POST route
old2 = "    def do_POST(self):\n        if not self._auth():"
assert old2 in s
new2 = '''    def do_POST(self):
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
        if not self._auth():'''
s = s.replace(old2, new2, 1)
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl)); print("ok")
