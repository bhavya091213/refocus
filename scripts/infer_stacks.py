"""Generate full-size 9-frame focal stacks with a fine-tuned U-Net.

Runs ON the GPU instance, from the root of the authors' repo (it imports their
simple_inference / simple_pipeline, the same way scripts/infer_server.py does).

usage: python infer_stacks.py <unet_dir> <out_dir> <input_pos> <scene_dir> [<scene_dir> ...]

Each scene_dir holds the 9 real photos of one scene (sorted file names = focus
order). Only the photo at <input_pos> is given to the model. For every scene this
writes <out_dir>/<scene>/frame_0..8.jpg (model output) and gt_0..8.jpg (real
photos at the same size), and appends the scene's PSNR over the 8 non-input
frames to <out_dir>/psnr.tsv as a sanity check.
"""
import math
import os
import sys

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, os.getcwd())
import simple_inference as si  # noqa: E402  (authors' module, needs cwd on the path)
from simple_pipeline import StableVideoDiffusionPipeline  # noqa: E402
from diffusers import AutoencoderKLTemporalDecoder, UNetSpatioTemporalConditionModel  # noqa: E402
from transformers import CLIPVisionModelWithProjection  # noqa: E402

SVD = "stabilityai/stable-video-diffusion-img2vid"
MAX_PIXELS = int(os.environ.get("REFOCUS_MAXPIX", "600000"))  # 640x896 = 573,440 stays at native size


class Args:
    """Stand-in for the argparse namespace simple_inference.inference_on_image expects."""
    num_inference_steps = 25


def find_scale(h, w):
    s = 1.0
    while True:
        sh, sw = math.floor(h * s / 64) * 64, math.floor(w * s / 64) * 64
        if sh * sw <= MAX_PIXELS:
            return sh, sw
        s -= 0.01


def load_pipeline(unet_dir, device):
    enc = CLIPVisionModelWithProjection.from_pretrained(SVD, subfolder="image_encoder").requires_grad_(False).to(device).eval()
    vae = AutoencoderKLTemporalDecoder.from_pretrained(SVD, subfolder="vae", variant="fp16").requires_grad_(False).to(device, dtype=torch.float32).eval()
    unet = UNetSpatioTemporalConditionModel.from_pretrained(unet_dir).to(device).eval()
    return StableVideoDiffusionPipeline.from_pretrained(SVD, unet=unet, image_encoder=enc, vae=vae, torch_dtype=torch.float32)


def scene_name(path):
    """Dataset scenes live at <scene>/midsize/undistorted/RigCenter; use the scene folder, without the colon."""
    parts = [p for p in path.rstrip("/").split("/") if p]
    return next((p for p in parts if p.startswith("FSK_")), parts[-1]).replace(":", "")


def psnr(a, b):
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return 99.0 if mse == 0 else 10 * math.log10(255.0 ** 2 / mse)


def run_scene(pipe, device, scene_dir, out_dir, pos):
    files = sorted(f for f in os.listdir(scene_dir) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    if len(files) != 9:
        raise ValueError("%s has %d images, expected 9" % (scene_dir, len(files)))
    real = [Image.open(os.path.join(scene_dir, f)).convert("RGB") for f in files]
    batch = si.convert_to_batch(real[pos], input_focal_position=pos)
    with torch.no_grad():
        frames, _ = si.inference_on_image(Args, batch, pipe, device)
    frames = frames.float().clamp(0, 1)
    os.makedirs(out_dir, exist_ok=True)
    scores = []
    for i in range(9):
        arr = (frames[i].permute(1, 2, 0).cpu().numpy() * 255).round().astype(np.uint8)
        Image.fromarray(arr).save(os.path.join(out_dir, "frame_%d.jpg" % i), quality=95)
        gt = real[i].resize((arr.shape[1], arr.shape[0]), Image.LANCZOS)
        gt.save(os.path.join(out_dir, "gt_%d.jpg" % i), quality=95)
        if i != pos:
            scores.append(psnr(arr, np.asarray(gt)))
    return sum(scores) / len(scores), arr.shape[1], arr.shape[0]


def main():
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    unet_dir, out_root, pos, scenes = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4:]
    if not 0 <= pos <= 8:
        sys.exit("input_pos must be 0..8")
    si.find_scale = find_scale
    device = torch.device("cuda")
    pipe = load_pipeline(unet_dir, device)
    os.makedirs(out_root, exist_ok=True)
    for scene_dir in scenes:
        name = scene_name(scene_dir)
        score, w, h = run_scene(pipe, device, scene_dir, os.path.join(out_root, "%s_in%d" % (name, pos)), pos)
        with open(os.path.join(out_root, "psnr.tsv"), "a") as f:
            f.write("%s\t%d\t%.2f\t%dx%d\n" % (name, pos, score, w, h))
        print("done %s in%d psnr %.2f %dx%d" % (name, pos, score, w, h), flush=True)
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
