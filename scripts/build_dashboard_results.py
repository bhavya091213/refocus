"""Build dashboard/public/results/summary.json (+ copies of sample sheets) from results/eval_*/metrics.json.
Adds paired statistics (same 60 items for every model), per-frame-index and per-distance curves, per-scene table."""
import json, math, os, shutil
import numpy as np
R = "D:/Refocus/results"; OUT = "D:/Refocus/dashboard/public/results"
os.makedirs(OUT, exist_ok=True)
NAMES = {"authors200k": "Authors' 200k checkpoint", "armA_random": "A: random (ours, 4k)", "armB_ablate_position": "B: ablate_position (ours, 4k)", "armC_ablate_time": "C: ablate_time (ours, 4k)"}
M = {k: json.load(open(f"{R}/eval_{k}/metrics.json")) for k in NAMES}
def item_means(m, key):
    return {(it["scene"], it["in_pos"]): float(np.mean([f[key] for f in it["frames"] if f["i"] != it["in_pos"]])) for it in m["items"]}
keys = ["psnr", "ssim", "lpips"]
IM = {k: {q: item_means(M[k], q) for q in keys} for k in M}
items = sorted(IM["authors200k"]["psnr"].keys())
def pair(a, b, q):
    d = np.array([IM[a][q][i] - IM[b][q][i] for i in items]); n = len(d)
    se = d.std(ddof=1) / math.sqrt(n); return dict(mean=float(d.mean()), se=float(se), t=float(d.mean() / se), wins=int((d > 0).sum()), n=n)
out = {"models": [], "paired": [], "by_frame": {}, "by_dist": {}, "scenes": [], "sheets": {}}
for k, m in M.items():
    s = m["summary"]; out["models"].append(dict(key=k, name=NAMES[k], **{q: s[q] for q in keys}, **{q + "_se": s[q + "_se"] for q in keys},
        rho=s["depth_consistency_rho"], gt_rho=s["gt_depth_consistency_rho"], psnr_by_pos=s["psnr_by_pos"], ssim_by_pos=s["ssim_by_pos"], lpips_by_pos=s["lpips_by_pos"]))
    pf = np.zeros(9); cnt = np.zeros(9); dd = {}
    for it in m["items"]:
        for f in it["frames"]:
            if f["i"] == it["in_pos"]: continue
            pf[f["i"]] += f["psnr"]; cnt[f["i"]] += 1; dd.setdefault(abs(f["i"] - it["in_pos"]), []).append(f["psnr"])
    out["by_frame"][k] = [round(float(a / b), 3) if b else None for a, b in zip(pf, cnt)]
    out["by_dist"][k] = {str(d): round(float(np.mean(v)), 3) for d, v in sorted(dd.items())}
for a, b in (("armA_random", "armB_ablate_position"), ("armA_random", "armC_ablate_time"), ("armB_ablate_position", "armC_ablate_time"), ("authors200k", "armA_random")):
    out["paired"].append(dict(a=NAMES[a], b=NAMES[b], **{q: pair(a, b, q) for q in keys}))
for sc in sorted({i[0] for i in items}):
    row = {"scene": sc}
    for k in M:
        row[k] = round(float(np.mean([IM[k]["psnr"][i] for i in items if i[0] == sc])), 2)
    out["scenes"].append(row)
for k in M:
    out["sheets"][k] = []
    for p in (1, 4, 7):
        src = f"{R}/eval_{k}/sheet_in{p}.jpg"
        if os.path.exists(src):
            os.makedirs(f"{OUT}/{k}", exist_ok=True); shutil.copy(src, f"{OUT}/{k}/sheet_in{p}.jpg"); out["sheets"][k].append(f"results/{k}/sheet_in{p}.jpg")
json.dump(out, open(f"{OUT}/summary.json", "w"), indent=1)
for p in out["paired"]: print(p["a"], "-", p["b"], {q: (round(p[q]["mean"], 4), round(p[q]["t"], 2), f'{p[q]["wins"]}/{p[q]["n"]}') for q in keys})
print("dist A", out["by_dist"]["armA_random"], "auth", out["by_dist"]["authors200k"])
