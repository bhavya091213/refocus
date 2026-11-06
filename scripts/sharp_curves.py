import json, sys
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
root = "/home/ubuntu/refocus"
ROIS = {"duck (0.8 m)": (0.08, 0.38, 0.62, 0.92), "bust (1.7 m)": (0.33, 0.62, 0.13, 0.52), "cat (4.8 m)": (0.68, 0.88, 0.22, 0.47)}  # x0,x1,y0,y1 normalised
def lapvar(img, roi):
    a = np.asarray(img.convert("L"), dtype=np.float64); H, W = a.shape
    x0, x1, y0, y1 = roi; c = a[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
    l = -4 * c[1:-1, 1:-1] + c[:-2, 1:-1] + c[2:, 1:-1] + c[1:-1, :-2] + c[1:-1, 2:]
    return float(l.var())
res = {}
jobs = [("still_life", 2, "f/1.4"), ("still_f4", 2, "f/4")]
fig, axs = plt.subplots(len(jobs), 3, figsize=(13, 4.2 * len(jobs)))
for r, (sc, k, lab) in enumerate(jobs):
    out = f"{root}/learn2refocus/outputs/blender/{sc}_in{k}/validation_images/focal_position_000{k}"
    for c, (name, roi) in enumerate(ROIS.items()):
        gt = [lapvar(Image.open(f"{root}/blender_in/renders/{sc}/focal_position_000{i}.png").resize((576, 832)), roi) for i in range(9)]
        md = [lapvar(Image.open(f"{out}/frame_{i}.png"), roi) for i in range(9)]
        g, m = np.array(gt), np.array(md)
        corr = float(np.corrcoef(g, m)[0, 1]); res[f"{lab}|{name}"] = dict(gt=[round(x, 2) for x in gt], model=[round(x, 2) for x in md], corr=round(corr, 2),
            gt_range=round(float(g.max() / max(g.min(), 1e-9)), 2), model_range=round(float(m.max() / max(m.min(), 1e-9)), 2))
        ax = axs[r][c]; ax.plot(range(9), g / g.max(), "o-", label="ground truth"); ax.plot(range(9), m / max(g.max(), 1e-9), "s--", label="model")
        ax.set_title(f"{lab} · {name}\ncorr={corr:.2f}", fontsize=10); ax.set_xlabel("focus position"); ax.set_ylabel("sharpness (norm. to GT max)"); ax.axvline(k, color="gray", ls=":")
        if r == 0 and c == 0: ax.legend()
plt.tight_layout(); plt.savefig(f"{root}/sharp_curves.png", dpi=110)
json.dump(res, open(f"{root}/sharp_curves.json", "w"), indent=1)
for key, v in res.items(): print(f"{key:22} corr {v['corr']:5}  GT max/min {v['gt_range']:6}  model max/min {v['model_range']:6}")
