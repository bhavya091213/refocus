"""Macro scene: per-object sharpness vs focus position, ground truth (Blender) vs model. By construction (README scale assumed linear in diopters)
the ground truth peaks at duck=4 (0.10 m), apple=5 (0.133 m), bust=6 (0.20 m), cat=7 (0.40 m). Reports the model's peak positions and the shift."""
import json, sys
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.ndimage import laplace
root = "/home/ubuntu/refocus"
ROIS = {"duck (0.10 m -> pos 4)": (0.09, 0.38, 0.38, 0.70, 4), "apple (0.133 m -> pos 5)": (0.58, 0.90, 0.43, 0.62, 5),
        "bust (0.20 m -> pos 6)": (0.38, 0.57, 0.24, 0.48, 6), "cat (0.40 m -> pos 7)": (0.62, 0.90, 0.13, 0.38, 7)}
def lapvar(img, roi):
    a = np.asarray(img.convert("L"), dtype=np.float64); H, W = a.shape
    x0, x1, y0, y1 = roi[:4]; c = a[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
    return float(laplace(c).var())
inputs = [int(x) for x in sys.argv[1:]] or [4, 6]
fig, axs = plt.subplots(len(inputs), 4, figsize=(15, 3.6 * len(inputs)), squeeze=False); res = {}
for r, k in enumerate(inputs):
    out = f"{root}/learn2refocus/outputs/blender/macro_in{k}/validation_images/focal_position_000{k}"
    for c, (name, roi) in enumerate(ROIS.items()):
        gt = np.array([lapvar(Image.open(f"{root}/blender_in/renders/macro/focal_position_000{i}.png").resize((576, 832)), roi) for i in range(9)])
        md = np.array([lapvar(Image.open(f"{out}/frame_{i}.png").resize((576, 832)), roi) for i in range(9)])
        res[f"in{k}|{name}"] = dict(expected_peak=roi[4], gt_peak=int(gt.argmax()), model_peak=int(md.argmax()), corr=round(float(np.corrcoef(gt, md)[0, 1]), 2),
                                    gt=[round(float(x), 2) for x in gt], model=[round(float(x), 2) for x in md])
        ax = axs[r][c]; ax.plot(range(9), gt / gt.max(), "o-", label="ground truth"); ax.plot(range(9), md / gt.max(), "s--", label="model")
        ax.axvline(roi[4], color="green", ls=":", label="expected peak"); ax.axvline(k, color="gray", ls=":")
        ax.set_title(f"input pos {k} - {name}\nGT peak {gt.argmax()}, model peak {md.argmax()}, corr {res[f'in{k}|{name}']['corr']}", fontsize=9); ax.set_xlabel("focus position")
        if r == 0 and c == 0: ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(f"{root}/macro_curves.png", dpi=105); json.dump(res, open(f"{root}/macro_curves.json", "w"), indent=1)
for k_, v in res.items(): print(f"{k_:34} expected {v['expected_peak']}  GT peak {v['gt_peak']}  model peak {v['model_peak']}  shift {v['model_peak'] - v['gt_peak']:+d}  corr {v['corr']}")
