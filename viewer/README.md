# Click-to-refocus viewer

A static, dependency-free web page (HTML/JS/CSS). It loads a 9-frame focal stack, and when you click a point it shows the frame that is sharpest there. Sharpness is computed in your browser: variance of the Laplacian in a window around the click, from integral images of the grayscale frames. A toggle shows a coarse depth-like map (index of the sharpest frame per cell, near = warm, far = cool).

**Credit.** The task, the 9-frame focal-stack formulation and the released model come from Tedla, Zhang, Zhang and Xin, *Learning to Refocus with Video Diffusion Models*, SIGGRAPH Asia 2025 (https://learn2refocus.github.io/). This viewer is our own class-project code; the refocus choice is a classical sharpness measure, not part of the paper.

## Run

```
cd D:\Refocus\viewer
python -m http.server 8765
# open http://localhost:8765/
```

It must be served over http (the page fetches `stacks/index.json`); opening `index.html` as a file will not work.

## Stacks

`python -I build_stacks.py` (needs Pillow) rebuilds `stacks/<name>/frame_0..8.jpg` and `stacks/index.json` from project outputs:

| Stack | Source |
|---|---|
| `real_scene` | real smartphone focal stack from the dataset (a test scene) |
| `authors_in4`, `authors_in1`, `authors_in7` | authors' 200k checkpoint output from one input frame (position 4 / 1 / 7); 180x252 crops from our evaluation contact sheets |
| `ours_random_in4` | our 4,000-step arm A (`random`), same scene, input position 4 |
| `blender_macro`, `blender_garden`, `blender_still_life` | Cycles thin-lens renders of CC0 Poly Haven assets (`blender/make_scene.py`) |

You can also use **Upload 9 frames** to pick nine same-sized images; they are used in file-name order (first = nearest).

## Making a stack from a new photo

This needs a GPU (about 25 GB VRAM, about 65 s per image on an A100) and is not run by the viewer.

1. Resize/crop the photo to the model's 640x896 portrait size and save it as RGB (not RGBA).
2. Run the authors' inference from https://github.com/tedlasai/learn2refocus with their released checkpoint, passing the photo as the input frame and its (assumed) focal position; our wrapper scripts are `scripts/remote_macro_infer.sh` and `scripts/remote_blender_infer.sh`. The model writes `frame_0.png` ... `frame_8.png`.
3. Copy the nine frames into `stacks/<name>/` as `frame_0.jpg`..`frame_8.jpg`, add an entry to `stacks/index.json` (or just use the Upload button).

## Caveats

- Position-to-distance spacing is not documented by the authors; only the near-to-far order is reliable.
- Low-texture regions (walls, sky) have almost flat sharpness curves, so the choice there is unreliable; the viewer warns when this happens.
- The authors' model outputs here are small crops (180x252) taken from our evaluation sheets; regenerate full-size frames on a GPU for a sharper demo.
