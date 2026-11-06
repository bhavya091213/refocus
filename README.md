# refocus

Single-image refocusing: take one photo, generate a **focal stack** (the same scene at 9 focus settings), and click any pixel to bring it into focus.

This is a course final project. It is a **reproduction and small controlled ablation** of someone else's research, not original research. All credit for the method, the dataset and the released model goes to the authors below.

## Original work (please cite it)

> SaiKiran Tedla, Zhoutong Zhang, Xuaner Zhang, Shumian Xin.
> **Learning to Refocus with Video Diffusion Models.**
> ACM SIGGRAPH Asia 2025. (Adobe Research; York University)

- Project page: <https://learn2refocus.github.io/>
- Paper: <https://dl.acm.org/doi/10.1145/3757377.3763873>
- Official code: <https://github.com/tedlasai/learn2refocus> (code licence: MIT, per the repo)
- Released checkpoint: <https://huggingface.co/tedlasai/learn2refocus>
- Dataset: linked from the project page ("Download Full Dataset")

```bibtex
@inproceedings{Tedla2025Refocus,
  title     = {Learning to Refocus with Video Diffusion Models},
  author    = {Tedla, SaiKiran and Zhang, Zhoutong and Zhang, Xuaner and Xin, Shumian},
  booktitle = {Proceedings of the ACM SIGGRAPH Asia Conference},
  year      = {2025}
}
```

The base model is Stable Video Diffusion (`stabilityai/stable-video-diffusion-img2vid`, Blattmann et al., 2023, arXiv:2311.15127) and is covered by Stability AI's own licence. The diffusion formulation follows Karras et al., *Elucidating the Design Space of Diffusion-Based Generative Models*, NeurIPS 2022.

## What this repo contains

| Path | What |
|---|---|
| `report/main.tex` | The LaTeX report, written alongside the work (architecture, data, training, ablation) |
| `dashboard/` | A small stdlib-only monitoring dashboard (progress checklist, loss curve, sample images, logs) |
| `scripts/` | Our own helper scripts (added as we go) |

**Not included on purpose:** the authors' code (clone it from the link above), the dataset, model weights and our dashboard credentials. See `.gitignore`.

## How the original method works (short version)

A focal stack is treated as a **video** whose frames are focus positions. Stable Video Diffusion is fine-tuned so that, given one photo and its focus position, it denoises a 9-frame latent video. The VAE and CLIP encoder are frozen and only the U-Net's temporal transformer blocks are trained. Details and sources are in the report.

## Our contribution

1. Run the authors' released checkpoint as the quality ceiling.
2. Fine-tune the same model ourselves under a small budget (cloud GPU, under $100).
3. A controlled ablation on how the input image and its focus position are presented to the network.
4. A click-to-refocus viewer that picks the sharpest generated frame at the clicked pixel.

Results will be filled in as they are produced. Nothing here is a claim of matching the authors' numbers.

## Reproducing

```bash
git clone https://github.com/tedlasai/learn2refocus code/learn2refocus   # authors' code, branch dev
# dataset: download the "midsize_undistorted" ZIPs from the project page into data/
# report:
cd report && tectonic main.tex
```
