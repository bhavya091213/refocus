"""Exploration: does monocular depth explain WHICH focal frame is sharpest at each pixel (real dataset)?
For N test scenes: (1) per-pixel argmax-sharpness frame index from the real 9-frame stack (a depth-from-focus proxy);
(2) monocular relative depth (Depth Anything V2 Small) from the middle frame; (3) Spearman correlation + the median disparity per position."""
import json, os, pickle, sys
import numpy as np, torch
from PIL import Image
from scipy.ndimage import uniform_filter, laplace
from scipy.stats import spearmanr
from transformers import pipeline
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
root = "/home/ubuntu/refocus"; N = int(sys.argv[1]) if len(sys.argv) > 1 else 16
te = pickle.load(open(root + "/learn2refocus/splits/test_scenes.pkl", "rb"))
base = root + "/data/scenes_merged_midsize_undistorted_RigCenter"
scenes = sorted(s for s in te if os.path.isdir(f"{base}/{s}"))[:: max(1, len(te) // N)][:N]
dp = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=0)
rhos, med = [], []
for sc in scenes:
    d = f"{base}/{sc}/midsize/undistorted/RigCenter"
    ims = [Image.open(f"{d}/focal_position_{i:04d}_frame_0000.jpg").convert("RGB") for i in range(9)]
    g = [np.asarray(im.convert("L"), dtype=np.float32) for im in ims]
    S = np.stack([uniform_filter(np.abs(laplace(a)), 21) for a in g])         # sharpness per frame
    idx = S.argmax(0); conf = S.max(0) / (S.mean(0) + 1e-6)
    disp = np.asarray(dp(ims[4])["predicted_depth"].float().cpu() if hasattr(dp(ims[4])["predicted_depth"], "cpu") else dp(ims[4])["predicted_depth"], dtype=np.float32)
    disp = np.asarray(Image.fromarray(disp).resize(ims[0].size, Image.BILINEAR)); disp = (disp - disp.min()) / (np.ptp(disp) + 1e-6)  # 1 = near (disparity)
    m = conf > np.percentile(conf, 60)                                        # textured pixels with a clear peak
    rho = spearmanr(idx[m], disp[m]).correlation; rhos.append(float(rho))
    med.append([float(np.median(disp[m & (idx == k)])) if (m & (idx == k)).sum() > 200 else np.nan for k in range(9)])
    print(f"{sc}: spearman(idx, disparity)={rho:+.2f}  usable px={m.mean():.0%}", flush=True)
med = np.array(med); mean_curve = np.nanmean(med, 0)
print("mean Spearman", round(float(np.mean(rhos)), 3), "| scenes", len(rhos), "| positive-corr scenes", sum(r > 0 for r in rhos))
print("median normalised disparity (1=near) of pixels sharpest at position k:", np.round(mean_curve, 2).tolist())
fig, ax = plt.subplots(1, 2, figsize=(11, 4)); ax[0].hist(rhos, bins=12); ax[0].set_title("per-scene Spearman(sharpest-frame idx, mono-depth disparity)"); ax[0].axvline(0, color="k")
for r in med: ax[1].plot(range(9), r, color="gray", alpha=.35)
ax[1].plot(range(9), mean_curve, "o-", lw=2.5); ax[1].set_xlabel("focus position (frame index)"); ax[1].set_ylabel("normalised disparity (1 = near)"); ax[1].set_title("which depth is sharpest at each position")
plt.tight_layout(); plt.savefig(root + "/depth_vs_focus.png", dpi=110)
json.dump({"scenes": scenes, "spearman": rhos, "median_disp_per_pos": med.tolist(), "mean_curve": mean_curve.tolist()}, open(root + "/depth_vs_focus.json", "w"))
