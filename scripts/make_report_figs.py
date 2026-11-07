"""Figures for the report, built from results/eval_*/metrics.json, dashboard/public/results/summary.json and dashboard/metrics.jsonl."""
import json, math, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
R = "D:/Refocus/"; O = R + "report/"
S = json.load(open(R + "dashboard/public/results/summary.json"))
COL = {"authors200k": "#6b7280", "armA_random": "#2563eb", "armB_ablate_position": "#d97706", "armC_ablate_time": "#059669"}
SHORT = {"authors200k": "Authors'\n200k", "armA_random": "A\nrandom", "armB_ablate_position": "B\nablate_position", "armC_ablate_time": "C\nablate_time"}
LONG = {"authors200k": "Authors' 200k checkpoint", "armA_random": "A: random (ours, 4k)", "armB_ablate_position": "B: ablate_position (ours, 4k)", "armC_ablate_time": "C: ablate_time (ours, 4k)"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
M = S["models"]; keys = [m["key"] for m in M]

# ---- 1. headline metrics with standard-error bars
fig, axs = plt.subplots(1, 3, figsize=(10, 3.1))
for ax, (q, name, hi) in zip(axs, (("psnr", "PSNR (dB) $\\uparrow$", True), ("ssim", "SSIM $\\uparrow$", True), ("lpips", "LPIPS $\\downarrow$", False))):
    v = np.array([m[q] for m in M]); e = np.array([m[q + "_se"] for m in M])
    ax.bar(range(4), v, yerr=e, color=[COL[k] for k in keys], capsize=3)
    lo = v.min() - (v.max() - v.min()) * 0.9; ax.set_ylim(lo, v.max() + (v.max() - v.min()) * 0.25)
    for i, (a, b) in enumerate(zip(v, e)): ax.text(i, a + b + (v.max() - v.min()) * 0.03, f"{a:.3f}" if q != "psnr" else f"{a:.2f}", ha="center", fontsize=8)
    ax.set_xticks(range(4)); ax.set_xticklabels([SHORT[k] for k in keys], fontsize=7.5); ax.set_title(name)
    ax.text(0.01, -0.28, f"axis starts at {lo:.2f}", transform=ax.transAxes, fontsize=7, color="#6b7280")
plt.tight_layout(); plt.savefig(O + "fig_results.pdf"); plt.close()

# ---- 2. paired differences with 95% CI
fig, axs = plt.subplots(1, 3, figsize=(10, 2.6))
for ax, (q, name) in zip(axs, (("psnr", "$\\Delta$PSNR (dB)"), ("ssim", "$\\Delta$SSIM"), ("lpips", "$\\Delta$LPIPS"))):
    for i, p in enumerate(S["paired"][:3][::-1] + S["paired"][3:]):
        r = p[q]; ci = 1.98 * r["se"]
        ax.errorbar(r["mean"], i, xerr=ci, fmt="o", color="#111827", capsize=3)
    labs = [f'{p["a"].split(" (")[0].split(":")[0]} $-$ {p["b"].split(" (")[0].split(":")[0]}' for p in S["paired"][:3][::-1] + S["paired"][3:]]
    ax.set_yticks(range(4)); ax.set_yticklabels(["B $-$ C", "A $-$ C", "A $-$ B", "Authors $-$ A"] if True else labs, fontsize=8)
    ax.axvline(0, color="#9ca3af", lw=0.8); ax.set_title(name); ax.grid(axis="x", alpha=0.25)
plt.tight_layout(); plt.savefig(O + "fig_paired.pdf"); plt.close()

# ---- 3. error vs distance and per-target-frame
fig, axs = plt.subplots(1, 2, figsize=(10, 3))
for k in keys:
    d = S["by_dist"][k]; xs = [int(i) for i in d]; axs[0].plot(xs, [d[str(i)] for i in xs], "o-", color=COL[k], label=LONG[k], ms=3)
    f = S["by_frame"][k]; axs[1].plot(range(9), [np.nan if a is None else a for a in f], "o-", color=COL[k], ms=3)
axs[0].set_xlabel("|target position $-$ input position|"); axs[0].set_ylabel("PSNR (dB)"); axs[0].legend(fontsize=7); axs[0].set_title("Error grows with distance from the input")
axs[1].set_xlabel("target focus position"); axs[1].set_ylabel("PSNR (dB)"); axs[1].set_title("PSNR by target position (inputs 1, 4, 7 pooled)")
for ax in axs: ax.grid(alpha=0.25)
plt.tight_layout(); plt.savefig(O + "fig_dist.pdf"); plt.close()

# ---- 4. training loss
rows = [json.loads(l) for l in open(R + "dashboard/metrics.jsonl") if l.strip()]
runs = {}
for r in rows:
    if r.get("loss") is not None and r.get("run"): runs.setdefault(r["run"], []).append((r["step"], r["loss"]))
fig, axs = plt.subplots(1, 2, figsize=(10, 2.9))
for run, c in (("armA_random", COL["armA_random"]), ("armB_ablate_position", COL["armB_ablate_position"]), ("armC_ablate_time", COL["armC_ablate_time"])):
    a = sorted(runs[run]); st = np.array([x[0] for x in a]); ls = np.array([x[1] for x in a])
    sm = np.array([ls[max(0, i - 14):i + 1].mean() for i in range(len(ls))])
    axs[0].plot(st, sm, color=c, lw=1.4, label=LONG[run])
    blocks = [ls[(st > b) & (st <= b + 1000)].mean() for b in range(0, 4000, 1000)]
    axs[1].plot([500, 1500, 2500, 3500], blocks, "o-", color=c, ms=4)
axs[0].set_xlabel("optimiser step"); axs[0].set_ylabel("loss (15-point moving average)"); axs[0].legend(fontsize=7); axs[0].set_title("Training loss (logged every 20 steps)")
axs[1].set_xlabel("step (1000-step blocks)"); axs[1].set_ylabel("mean logged loss"); axs[1].set_title("Block means: arms are indistinguishable")
for ax in axs: ax.grid(alpha=0.25)
plt.tight_layout(); plt.savefig(O + "fig_loss.pdf"); plt.close()
for run in runs: print(run, len(runs[run]), "pts; last", sorted(runs[run])[-1])

# ---- 5. qualitative: ground truth + each model, same scene, input position 4
W, H = 180, 252
def rows_of(name):
    im = Image.open(R + f"results/eval_{name}/sheet_in4.jpg"); return im.crop((0, 0, 9 * W, H)), im.crop((0, H, 9 * W, 2 * H))
gt, _ = rows_of("authors200k")
labels = ["ground truth (real stack)"] + [LONG[k] for k in keys]
imgs = [gt] + [rows_of(k)[1] for k in keys]
fig, axs = plt.subplots(5, 1, figsize=(10, 6.6))
for ax, im, lab in zip(axs, imgs, labels):
    ax.imshow(im); ax.set_ylabel(lab, rotation=0, ha="right", va="center", fontsize=7.5); ax.set_yticks([])
    ax.set_xticks([W * i + W / 2 for i in range(9)]); ax.set_xticklabels([str(i) if ax is axs[-1] else "" for i in range(9)])
    ax.spines[:].set_visible(False); ax.tick_params(length=0)
axs[-1].set_xlabel("focus position (input photo = position 4)")
plt.tight_layout(); plt.savefig(O + "fig_qual.pdf"); plt.close()
print("figures ok")
