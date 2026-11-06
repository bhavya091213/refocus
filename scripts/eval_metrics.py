"""Score one model's generated stacks against the real stacks on the fixed test subset.
usage: python eval_metrics.py <name> <n_scenes> <positions comma list>
Reads  outputs/eval_<name>/validation_images/position_<p>/images/img_<j>_frame_<i>.png  (written by svd_runner test mode)
Writes outputs/eval_<name>/metrics.json  (+ contact sheets). Metrics: PSNR, SSIM, LPIPS(vgg) on the 8 frames that are NOT the input position,
plus the depth-consistency score (Spearman between argmax-sharpness frame index and Depth Anything V2 disparity)."""
import json, os, pickle, sys
import numpy as np, torch
from PIL import Image
from scipy.ndimage import uniform_filter, laplace
from scipy.stats import spearmanr
import lpips
from torchmetrics.functional.image import peak_signal_noise_ratio as psnr_fn, structural_similarity_index_measure as ssim_fn
from transformers import pipeline

name, n_scenes, positions = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")]
root = os.path.expanduser("~/refocus"); L2R = root + "/learn2refocus"
out = f"{L2R}/outputs/eval_{name}"; base = root + "/data/scenes_merged_midsize_undistorted_RigCenter"
te = set(pickle.load(open(L2R + "/splits/test_scenes.pkl", "rb")))
scenes = sorted(s for s in os.listdir(base) if s.replace("_", ":") in te or s in te)
scenes = [s for s in scenes if os.path.isdir(f"{base}/{s}/midsize/undistorted/RigCenter")]
scenes = scenes[::max(1, len(scenes) // n_scenes)][:n_scenes]
dev = "cuda"
lp = lpips.LPIPS(net="vgg").to(dev).eval()
dp = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=0)


def gt_frames(sc):
    d = f"{base}/{sc}/midsize/undistorted/RigCenter"
    return [Image.open(f"{d}/focal_position_{i:04d}_frame_0000.jpg").convert("RGB") for i in range(9)]


def tens(im): return torch.from_numpy(np.asarray(im, dtype=np.float32) / 255.0).permute(2, 0, 1)[None].to(dev)


def idx_map(frames):  # frames: list of 9 PIL -> (argmax idx, confidence)
    S = np.stack([uniform_filter(np.abs(laplace(np.asarray(f.convert("L"), dtype=np.float32))), 21) for f in frames])
    return S.argmax(0), S.max(0) / (S.mean(0) + 1e-6)


def rho(frames, disp):
    idx, conf = idx_map(frames); m = conf > np.percentile(conf, 60)
    return float(spearmanr(idx[m], disp[m]).correlation)


items, gt_rhos = [], []
for j, sc in enumerate(scenes):
    gt = gt_frames(sc)
    _pd = dp(gt[4])["predicted_depth"]
    disp = np.asarray(_pd.float().cpu() if hasattr(_pd, "cpu") else _pd, dtype=np.float32).squeeze()
    disp = np.asarray(Image.fromarray(disp).resize(gt[0].size, Image.BILINEAR)); disp = (disp - disp.min()) / (np.ptp(disp) + 1e-6)
    gt_rho = rho(gt, disp); gt_rhos.append(gt_rho)
    for p in positions:
        d = f"{out}/validation_images/position_{p}/images"
        gen = [Image.open(f"{d}/img_{j}_frame_{i}.png").convert("RGB") for i in range(9)]
        gen = [g.resize(gt[0].size) if g.size != gt[0].size else g for g in gen]
        per = []
        for i in range(9):
            a, b = tens(gen[i]), tens(gt[i])
            with torch.no_grad():
                per.append(dict(i=i, psnr=float(psnr_fn(a, b, data_range=1.0)), ssim=float(ssim_fn(a, b, data_range=1.0)), lpips=float(lp(a * 2 - 1, b * 2 - 1))))
        items.append(dict(scene=sc, in_pos=p, frames=per, rho=rho(gen, disp), gt_rho=gt_rho))
    print("scored", j + 1, "/", len(scenes), flush=True)

def agg(key, exclude_input=True):
    v = [f[key] for it in items for f in it["frames"] if (not exclude_input or f["i"] != it["in_pos"])]
    return float(np.mean(v)), float(np.std(v) / np.sqrt(len(v)))

res = {"name": name, "n_scenes": len(scenes), "positions": positions, "n_items": len(items)}
for k in ("psnr", "ssim", "lpips"):
    m, se = agg(k); res[k] = round(m, 4); res[k + "_se"] = round(se, 4)
    res[k + "_by_pos"] = {str(p): round(float(np.mean([f[k] for it in items if it["in_pos"] == p for f in it["frames"] if f["i"] != p])), 4) for p in positions}
res["depth_consistency_rho"] = round(float(np.mean([it["rho"] for it in items])), 4)
res["gt_depth_consistency_rho"] = round(float(np.mean(gt_rhos)), 4)
json.dump({"summary": res, "items": items}, open(f"{out}/metrics.json", "w"))
print(json.dumps(res, indent=1))
# contact sheet for the figure: scene 0, each input position: GT row over model row
W, H = 180, 252
for p in positions[:3]:
    sheet = Image.new("RGB", (9 * W, 2 * H))
    gt = gt_frames(scenes[0])
    for i in range(9):
        sheet.paste(gt[i].resize((W, H)), (i * W, 0))
        sheet.paste(Image.open(f"{out}/validation_images/position_{p}/images/img_0_frame_{i}.png").convert("RGB").resize((W, H)), (i * W, H))
    sheet.save(f"{out}/sheet_in{p}.jpg", quality=90)
print("EVAL_METRICS_DONE")
