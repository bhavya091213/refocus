"""Download CC0 assets from Poly Haven (public API, no key). usage: fetch_polyhaven.py <outdir> model:<id> ... hdri:<id>"""
import json, os, sys, urllib.request
UA = {"User-Agent": "refocus-class-project/1.0"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
out = sys.argv[1]
for spec in sys.argv[2:]:
    kind, aid = spec.split(":"); d = f"{out}/{aid}"; os.makedirs(d, exist_ok=True)
    files = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
    if kind == "hdri":
        u = files["hdri"]["1k"]["hdr"]["url"]; open(f"{d}/{aid}_1k.hdr", "wb").write(get(u)); print("hdri", aid); continue
    g = files["gltf"]["1k"]["gltf"]; open(f"{d}/{aid}.gltf", "wb").write(get(g["url"]))
    for rel, meta in g.get("include", {}).items():
        p = f"{d}/{rel}"; os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(get(meta["url"]))
    print("model", aid, "files", 1 + len(g.get("include", {})))
