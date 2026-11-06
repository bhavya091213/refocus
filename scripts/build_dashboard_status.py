"""Rebuild dashboard/status.json (expandable steps with details + files) and copy assets into dashboard/public/steps/.
Run any time:  python -I scripts/build_dashboard_status.py   (idempotent). Edit STEPS below as the project progresses."""
import json, os, shutil, subprocess, urllib.request

R = "D:/Refocus/"; PUB = R + "dashboard/public/steps/"
SCR = "C:/Users/Raj/AppData/Local/Temp/claude/C--Windows-System32/960471f0-c3ff-421f-8954-03a25a2a9522/scratchpad/"
CODE = R + "code/learn2refocus/"
os.makedirs(PUB, exist_ok=True)


def put(slug, name, src=None, text=None):
    d = PUB + slug; os.makedirs(d, exist_ok=True)
    dst = d + "/" + name
    if text is not None: open(dst, "w", encoding="utf-8").write(text)
    elif src and os.path.exists(src): shutil.copy(src, dst)
    else: return None
    return {"name": name, "path": f"steps/{slug}/{name}"}


def lines(path, a, b):  # 1-indexed inclusive
    return "".join(open(path, encoding="utf-8").readlines()[a - 1:b])


def ssh(cmd):
    try:
        r = subprocess.run(["ssh", "-i", os.path.expanduser("~/.ssh/lambda_parakeet_ed25519"), "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8",
                            "-o", "UserKnownHostsFile=NUL", "ubuntu@150.136.66.111", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40)
        return r.stdout
    except Exception as e:
        return f"(ssh failed: {e})"


F = lambda *x: [i for i in x if i]
STEPS = []

# 1 ---------------------------------------------------------------------------------------------------------
STEPS.append(dict(title="Project folder, repo, LaTeX toolchain", state="done", note="github.com/bhavya091213/refocus · Tectonic",
    details="Everything lives in D:\\Refocus. Git repo pushed to https://github.com/bhavya091213/refocus (main). The README credits and cites the original paper "
            "(Tedla, Zhang, Zhang, Xin, 'Learning to Refocus with Video Diffusion Models', SIGGRAPH Asia 2025) and links the authors' code, checkpoint and dataset; "
            "their code/data/weights are NOT copied into our repo. CITATION.cff and the report bibliography cite the same sources.\n"
            "LaTeX is compiled locally with Tectonic 0.17 (no Overleaf needed). The report is written alongside the work.",
    files=F(put("s1", "report.pdf", R + "report/main.pdf"), put("s1", "README.md", R + "README.md"), put("s1", "CITATION.cff", R + "CITATION.cff"), put("s1", "main.tex", R + "report/main.tex"))))

# 2 ---------------------------------------------------------------------------------------------------------
runner = CODE + "training/svd_runner.py"
STEPS.append(dict(title="Read training code, document architecture", state="done", note="Frozen VAE+CLIP · train UNet temporal blocks only · 9-frame stack",
    details="Base model: stabilityai/stable-video-diffusion-img2vid (latent video diffusion). Three parts:\n"
            " • VAE (AutoencoderKLTemporalDecoder): frame <-> 4-channel latent at 1/8 resolution. FROZEN.\n"
            " • CLIP image encoder: embeds the input photo, used through cross-attention. FROZEN.\n"
            " • Denoising UNet (UNetSpatioTemporalConditionModel): spatial layers (how one image looks) + temporal layers (how frames relate). "
            "ONLY parameters whose name contains 'temporal_transformer_block' are trained; everything else is frozen.\n\n"
            "A focal stack is treated as a 9-frame video: frame j = photo focused at position j (0 = nearest ~5 cm ... 8 = infinity).\n"
            "Input conditioning (mode 'random'): pick a random frame k as the observed input; put its VAE latent in slot k of 9 and zero the other slots; concatenate with the 4-channel "
            "noisy latent -> 8 input channels. The slot index tells the network which focus position the input has. The CLIP embedding of frame k goes in via cross-attention.\n"
            "Loss: EDM-style denoising MSE in latent space, weighted (1+sigma^2)/sigma^2, sigma ~ LogNormal(0.7, 1.6).\n"
            "Authors' defaults: AdamW lr 1e-5 constant, batch 1/GPU, fp32, no EMA, 640x896, 200,000 steps (released checkpoint).\n"
            "Open code excerpts below (conditioning, freezing rule, loss).",
    files=F(put("s2", "conditioning_modes.py", text=lines(runner, 462, 547)), put("s2", "freeze_rule_and_optimizer.py", text=lines(runner, 255, 278)),
            put("s2", "loss.py", text=lines(runner, 549, 569)), put("s2", "authors_train_config.yaml", CODE + "training/configs/focal_stacks_train.yaml"),
            put("s2", "dataset_class.py", text=lines(CODE + "training/utils.py", 148, 240)))))

# 3 ---------------------------------------------------------------------------------------------------------
STEPS.append(dict(title="Dataset downloaded + verified", state="done", note="1,638 complete scenes · 1,474 train / 164 test",
    details="Used file: scenes_merged_midsize_undistorted_RigCenter.zip (943.8 MB; 7.3 GB extracted) + splits.zip, downloaded from the authors' sync.com share by driving a real browser (Playwright).\n"
            "Contents: 1,643 scene folders, 14,764 JPEGs, each 640x896. 1,638 scenes have all 9 focal positions; 5 folders are incomplete (1,2,4,7,8 frames) and belong to no split.\n"
            "Splits (identical to the repo's): 1,474 train, 164 test, zero overlap. Scenes span 17 capture days, Aug-Dec 2024.\n"
            "Not downloaded on purpose: full-size / DNG / other-rig archives (17-51 GB each). Reasoning: they are the same scenes at higher resolution or from slightly shifted viewpoints; the training code resizes to 640x896 anyway.\n\n"
            "PREPROCESSING LOG\n"
            " 1. Sort the 9 JPEGs by file name -> focal order 0..8.\n"
            " 2. Resize to 640x896 (no-op, already that size).\n"
            " 3. Scale pixels 0..255 -> -1..1.\n"
            " 4. Encode each frame with the frozen VAE -> latent 9x4x112x80.\n"
            " Windows gotcha: scene names contain ':' (GMT-05:00) which Windows turns into '_' on extraction, so split lists stop matching. We extract on the Linux GPU machine instead.\n"
            " No cropping, no colour changes, no extra augmentation.",
    files=F(put("s3", "sample_stack_pos0.jpg", R + "remotion/public/frames/f0.jpg"), put("s3", "sample_stack_pos4.jpg", R + "remotion/public/frames/f4.jpg"),
            put("s3", "sample_stack_pos8.jpg", R + "remotion/public/frames/f8.jpg"), put("s3", "dataset_stats.py", R + "scripts/dataset_stats.py"))))

# 4 ---------------------------------------------------------------------------------------------------------
setup_log = ssh("tail -n 12 ~/setup.log")
STEPS.append(dict(title="Lambda instance up, env + weights + data on it", state="done", note="1x A100 40GB · torch 2.6.0 · diffusers 0.32.0",
    details="Instance: gpu_1x_a100_sxm4 (A100 40 GB), us-east-1, $1.99/hr, key 'parakeet-gujarati'. H100s had no capacity.\n"
            "A local watchdog (scripts/watchdog.py) terminates the instance at a deadline unless extended - cost safety.\n"
            "Environment recreated with pip using the authors' pinned versions: torch 2.6.0+cu124, diffusers 0.32.0, transformers 4.50.0, accelerate 1.5.2, numpy 1.26.0, pillow 9.5.0.\n"
            "On the instance: SVD base weights (31 GB), authors' checkpoint-200000 (15 GB), dataset extracted (1,643 scenes).\n"
            "Spend and live GPU use are in the 'Lambda cloud' card above.",
    files=F(put("s4", "setup_log_tail.txt", text=setup_log), put("s4", "remote_setup.sh", R + "scripts/remote_setup.sh"), put("s4", "watchdog.py", R + "scripts/watchdog.py"))))

# 5 ---------------------------------------------------------------------------------------------------------
STEPS.append(dict(title="Baseline: authors' checkpoint on a test scene", state="done", note="works · ~2.5 s/denoise step · ~65 s per image · 25 GB VRAM",
    details="Ran the authors' 200k-step checkpoint on the first test scene, all 9 input positions (single GPU; their config assumes 4-GPU DeepSpeed, which we bypassed). 9 items took 10:58 wall-clock, ~65 s each (25 denoising steps at 2.5 s).\n"
            "Image below: top row = real photos at focus 0..8; middle row = model output generated from ONLY the input photo (bottom row, slot 0). The generated stack tracks the real one.\n"
            "Consequence for evaluation: the full test set (164 scenes x 9 positions = 1,476 items) would take ~26 GPU-hours (~$50), so metrics will use a subset.",
    files=F(put("s5", "baseline_contact_sheet.jpg", SCR + "sheet0.jpg"), put("s5", "contact_sheet.py", R + "scripts/contact_sheet.py"), put("s5", "remote_smoke.sh", R + "scripts/remote_smoke.sh"))))

# 6 ---------------------------------------------------------------------------------------------------------
STEPS.append(dict(title="Training benchmark: memory + step time", state="done", note="bf16 + grad-checkpointing: 1.71 s/step, 37.8 GB peak (fits 40 GB)",
    details="Goal: find out what training can afford before choosing runs.\n"
            " A) Authors' defaults (fp32, no checkpointing): CUDA out of memory at the very first step on the 40 GB A100.\n"
            " B) bf16 + gradient checkpointing: fits; step 1 took 3.3 s (warm-up). The authors' automatic validation then crashed (bf16 vs fp32 VAE input mismatch).\n"
            " C) Same as B with in-training validation switched off (REFOCUS_SKIP_VAL=1, our patch): 50 steps in 1 min 27 s = 1.71 s/step, peak GPU memory 37,811 MiB of 40,960, step loss 0.104 at step 50.\n"
            "Meaning: ~35 steps/min, ~2,100 steps/hour. At $1.99/hr that is roughly 1,000 steps per dollar. Headroom is thin (37.8 of 40 GB), so avoid larger resolution on this GPU.\n"
            "Deviations from the authors' training (to be stated in the report): bf16 mixed precision, gradient checkpointing, single GPU instead of 4, validation off during training.",
    files=F(put("s6", "remote_bench.sh", R + "scripts/remote_bench.sh"))))

# 7 ---------------------------------------------------------------------------------------------------------
STEPS.append(dict(title="Ablation chosen: random vs ablate_position vs ablate_time", state="done", note="3 arms, identical except `conditioning`",
    details="An ablation = change exactly ONE thing, keep data/steps/seed identical, so the quality gap is attributable to that thing.\n"
            "Modes already implemented in the authors' training script (conditioning:):\n"
            " • random (paper default): input latent in slot k, other slots zero -> position is implied by the slot.\n"
            " • ablate_position: input latent copied into ALL 9 slots -> no position signal. Question: does the model need to know the input's focus position?\n"
            " • ablate_time: same copy, but position k is passed through SVD's motion_bucket_id number. Question: does the position encoding matter?\n"
            " • zero: input is always frame 0.\n"
            "DECISION (user approved): three arms A=random (paper default), B=ablate_position, C=ablate_time. 'zero' dropped: it only ever sees the nearest-focus input, so testing at other positions is not a fair comparison.\n"
            "VERIFIED: svd_pipeline.py (inference) treats ablate_position / ablate_time exactly as training does (input latent repeated into all 9 slots; for ablate_time the position goes through motion_bucket_id).\n"
            "Questions: A vs B = does knowing the input's focus position help? A vs C = does HOW the position is encoded matter?",
    files=F(put("s7", "conditioning_modes.py", text=lines(runner, 462, 547)), put("s7", "svd_pipeline_conditioning_inference.py", text=lines(CODE + "training/svd_pipeline.py", 557, 590)))))

# 8 ---------------------------------------------------------------------------------------------------------
STEPS.append(dict(title="Fine-tune the 3 arms on 8x A100 (parallel) + evaluate", state="doing", note="instance setup in progress; training starts when ready",
    details="Budget changed by the user to up to $20/hr for ~3 hours. Instance: 8x A100 40GB (gpu_8x_a100, us-east-1) at $15.92/hr = $1.99 per GPU-hour, the same rate as one GPU: parallelism buys SPEED, not cheaper compute. Hard cap $65 enforced by a local watchdog.\n"
            "LAYOUT: GPUs 0-1 arm A (random) | 2-3 arm B (ablate_position) | 4-5 arm C (ablate_time) | 6 authors' checkpoint evaluation | 7 spare (Blender macro scene). Each arm trains with 2-GPU data parallelism, then is evaluated on its own GPU.\n"
            "TRAINING (identical for all arms except `conditioning`): SVD base, only temporal transformer blocks trained, seed 0, bf16 + gradient checkpointing, per-GPU batch 1 (global 2), lr 1e-5 x scale_lr 2 = 2e-5, AdamW, 4,000 steps = 8,000 samples (~5.4 passes over the 1,474 train scenes), checkpoints every 1,000 steps.\n"
            "DEVIATIONS from the authors (to state in the report): bf16 + checkpointing (fp32 OOMs on 40GB), 4,000 vs 200,000 steps (2%), no EMA, their hardware/batch is not stated, in-training validation disabled (crashes under bf16).\n"
            "EVALUATION (fixed subset): 20 test scenes x input positions {1,4,7} = 60 generations per model; metrics on the 8 non-input frames: PSNR, SSIM, LPIPS(vgg) + depth-consistency score (Spearman of sharpest-frame index vs monocular disparity). FID/VIF not reported (too few images).\n"
            "Pipeline smoke test (authors' checkpoint, 2 scenes x 3 positions): PSNR 32.7, SSIM 0.934, LPIPS 0.195, depth-rho -0.21 (real stacks -0.52). Pipeline works; numbers are from only 6 generations.\n"
            "Loss curves per run stream into the chart above; per-GPU metadata is in 'GPU details'.",
    files=F(put("s8", "run_ablation_8x.sh", R + "scripts/run_ablation_8x.sh"), put("s8", "eval_metrics.py", R + "scripts/eval_metrics.py"), put("s8", "remote_patch.py", R + "scripts/remote_patch.py"),
            put("s8", "setup_new_instance.sh", R + "scripts/setup_new_instance.sh"))))

# 9 ---------------------------------------------------------------------------------------------------------
STEPS.append(dict(title="Blender demo scenes (CC0 assets) -> model", state="doing", note="renders done · inference running",
    details="For the demo: build depth-layered scenes in Blender 4.5 from public-domain (CC0) Poly Haven models + HDRI lighting, render a TRUE ground-truth focal stack with Blender's thin-lens depth of field (9 focus distances), then give ONE frame to the model and compare its generated stack to the ground truth.\n"
            "Scenes: 'still_life' (duck 0.8 m, apple 0.9 m, bust 1.7 m, plant 3 m, cat 4.8 m) and 'garden' (rocks, duck, bust, tree, plant).\n"
            "Assets (CC0): marble_bust_01, potted_plant_02, rubber_duck_toy, food_apple_01, concrete_cat_statue, rock_moss_set_01, tree_small_02; HDRIs studio_small_09, kloofendal_48d_partly_cloudy_puresky. All from polyhaven.com.\n"
            "Rendered 640x896, Cycles, 48 samples + denoise, f/1.4 on the AMD RX 6900 XT (HIP). Focus distances: 0.45, 0.6, 0.85, 1.2, 1.8, 2.8, 4.5, 9, 200 m.\n"
            "CAVEATS: (1) mapping from the phone's lens positions 0..8 to these distances is our guess, not a calibration; (2) synthetic renders are a domain shift from smartphone photos; results are shown as-is.\n\n"
            "RESULT 1 (f/1.4, authors' 200k checkpoint; compare_* images: top row ground truth, middle row model, bottom row the single input). First impression from thumbnails: the model's stack looked nearly static. CORRECTION after measuring: it is NOT static, see Result 2.\n"
            "RESULT 2 (measured): local sharpness (variance of Laplacian) in boxes around the duck / bust / cat, per output frame, for ground truth vs model (chart: sharpness_curves.png, numbers in sharp_curves.json; single scene, single input position 2, single sample, hand-chosen boxes: indicative, not statistically conclusive).\n"
            " f/1.4: correlation GT-vs-model duck 0.00, bust -0.14, cat 0.20. f/4: duck 0.32, bust 0.46, cat 0.81.\n"
            " The model DOES sweep focus near-to-far in the right order (duck sharpest ~pos 3, bust ~pos 5, cat rising at 6-8), but its peaks arrive ~1-2 positions later than Blender's, are weaker for far objects, and it keeps the near duck sharp one position too long.\n"
            " Weaker blur (f/4) agrees much better than f/1.4 (supports, does not prove, 'our blur is far stronger than phone photos'). f/8 is uninformative: even the ground truth barely changes across positions.\n"
            "Likely remaining cause (NOT verified): our guessed mapping from position to focus distance. The README says positions 0..8 span 5 cm to infinity (iPhone lens position 0..0.8): if spacing is linear in diopters (assumption), positions 0..7 cover only ~5-40 cm, i.e. the dataset is macro-scale, while our scene spans 0.45-200 m. Next test: re-render a macro-scale scene (objects 0.1-0.6 m) with that mapping.\n\n"
            "RESULT 3 (macro scene, phone-like camera 7mm sensor / 6mm lens / f/1.8, objects at 0.10/0.133/0.20/0.40 m, assumed diopter-linear position scale so GT peaks at positions 4/5/6/7; duck ROI discarded - dominated by background texture): NOT a clean fix.\n"
            " Input pos 4: model peaks 1 position LATE for apple (6 vs 5), bust (7 vs 6), cat (8 vs 7); correct near-to-far order, qualitatively plausible (compare_macro_in4.jpg).\n"
            " Input pos 6: model peaks EARLY (apple 3 vs 5, bust 5 vs 6, cat 4 vs 7) and out of depth order.\n"
            " So the offset changes sign with the input position: it is not a fixed calibration error. We cannot separate a wrong distance-to-position assumption from the synthetic-vs-real domain shift without real photos at known distances. Single scene, single input each, indicative only.",
    files=F(put("s9", "ground_truth_still_life.jpg", SCR + "gt_still.jpg"), put("s9", "ground_truth_garden.jpg", SCR + "gt_garden.jpg"),
            put("s9", "make_scene.py", R + "blender/make_scene.py"), put("s9", "fetch_polyhaven.py", R + "scripts/fetch_polyhaven.py"))))
for extra in ("compare_still_life_in2.jpg", "compare_still_life_in6.jpg", "compare_garden_in2.jpg", "compare_garden_in5.jpg",
              "compare_still_f4_in2.jpg", "compare_still_f4_in6.jpg", "compare_still_f8_in2.jpg", "compare_still_f8_in6.jpg"):
    f = put("s9", extra, SCR + extra)
    if f: STEPS[-1]["files"].append(f)
for src, name in ((SCR + "macro_curves.png", "macro_peak_curves.png"), (SCR + "compare_macro_in4.jpg", "macro_compare_in4.jpg"), (SCR + "compare_macro_in6.jpg", "macro_compare_in6.jpg")):
    f = put("s9", name, src)
    if f: STEPS[-1]["files"].insert(0, f)
for src, name in ((SCR + "sharp_curves.png", "sharpness_curves.png"),):
    f = put("s9", name, src)
    if f: STEPS[-1]["files"].insert(0, f)
for src, name in ((R + "scripts/sharp_curves.py", "sharp_curves.py"),):
    f = put("s9", name, src)
    if f: STEPS[-1]["files"].append(f)
for extra in ():
    f = put("s9", extra, SCR + extra)
    if f: STEPS[-1]["files"].append(f)

# 13 extra credit --------------------------------------------------------------------------------------------
STEPS.append(dict(title="Extra credit: depth mapping and focus", state="doing", note="mono-depth agrees with focus stack: mean Spearman -0.80 (16 scenes)",
    details="Question: can depth help our refocusing predictions? In a focal stack the frame sharpest at a pixel is a depth proxy (depth-from-focus).\n"
            "EXPERIMENT 1 (done, real dataset, no training): 16 test scenes. Per pixel: index of the sharpest frame (abs Laplacian, 21x21 box) vs relative disparity from Depth Anything V2 Small on the middle frame; Spearman on the 40% most textured pixels.\n"
            "RESULT: mean rho = -0.80, all 16 scenes negative (range -0.97 to -0.35). Near pixels are sharpest at low positions, far at high. Median disparity of pixels sharpest at position 0..8: 0.59, 0.70, 0.70, 0.61, 0.48, 0.45, 0.26, 0.19, 0.22 (roughly flat over 0-2, then falling).\n"
            "CAVEATS: one depth model, 16 scenes, hand-chosen texture mask, relative (not metric) depth. Exploration, not a benchmark.\n\n"
            "OPPORTUNITIES (effort / payoff):\n"
            " A. Depth-consistency score for generated stacks: same correlation on the MODEL's output; label-free metric for the report and for ablation arms. Low effort, high value. (Real-data value -0.80 is the reference ceiling.)\n"
            " B. Classical baseline: monocular depth + synthetic lens blur from the single input (portrait-mode style) vs the diffusion model; shows what generation adds (it can sharpen, classical blur cannot). Medium effort.\n"
            " C. Depth as extra conditioning channel or auxiliary loss while fine-tuning. Highest potential, highest risk (changes the input layer, needs a training run ~$10-20). Stretch only.\n"
            " D. NYU Depth V2 (cs.nyu.edu/~fergus/datasets/nyu_depth_v2.html): 1,449 labelled RGB-D pairs (2.8 GB .mat), 464 scenes, Kinect; raw is ~428 GB (do not download). No licence stated on the page, cite only (Silberman et al., ECCV 2012). Use to validate the depth estimator or simulate focal stacks from RGB-D; caveats: Kinect holes, low resolution, domain gap. Low priority.\n"
            " E. Use the measured position-vs-depth curve to place objects in the Blender demo so it matches the phone's scale (likely the cause of the 1-2 position offset seen in Result 2). Low-medium effort.\n"
            "Recommended: A + E now, B if time, C only if budget remains, D minimal.",
    files=F(put("s13", "depth_vs_focus.png", SCR + "depth_vs_focus.png"), put("s13", "depth_vs_focus.py", R + "scripts/depth_vs_focus.py"))))
# the json copied earlier is also viewable
STEPS[-1]["files"].append({"name": "depth_vs_focus.json", "path": "steps/s13/depth_vs_focus.json"})

# 10-12 -----------------------------------------------------------------------------------------------------
STEPS.append(dict(title="Metrics on a test subset", state="todo", note="PSNR · SSIM · LPIPS · FID · VIF",
    details="Authors' extra/compute_metrics.py computes PSNR, SSIM, LPIPS (VGG), FID, VIF for every (input position, output position) pair over 164 test scenes. Full test = ~26 GPU-hours, so we will evaluate a fixed subset (same scenes/positions for every model) and say so in the report."))
STEPS.append(dict(title="Click-to-refocus demo + Remotion animations", state="todo", note="sharpness data computed from real frames",
    details="Click-to-refocus: local sharpness = variance of the Laplacian in a window around the clicked pixel, per generated frame; show the argmax frame. Real sample (from actual dataset frames): click (200,320) -> frame 0 sharpest; click (200,40) -> frame 7 sharpest.\n"
            "Remotion project scaffolded in D:\\Refocus\\remotion (sample frames + real sharpness data ready); animation scenes still to be written.",
    files=F(put("s11", "sharpness_samples.py", R + "scripts/sharpness_samples.py"), put("s11", "sharpness.json", R + "remotion/src/sharpness.json"))))
STEPS.append(dict(title="Report (LaTeX) + 3 slides", state="doing", note="architecture + data sections written",
    details="Report sections drafted: problem, why a video model, SVD, EDM loss, what is fine-tuned, hyperparameters, data + preprocessing log. Placeholders (red TBD) for results. Slides: 3 slides / 3 minutes not started.",
    files=F(put("s12", "report.pdf", R + "report/main.pdf"))))

status = {"kv": [["Phase", "Blender demo + training plan"], ["Base model", "SVD img2vid"], ["Train / test scenes", "1474 / 164"], ["Cloud", "1x A100 40GB, $1.99/hr"],
                 ["Train speed", "1.71 s/step (bf16)"], ["Ablation", "not chosen yet"]], "steps": STEPS}
json.dump(status, open(R + "dashboard/status.json", "w", encoding="utf-8"))
key = open(R + "dashboard/token.txt").read().strip()
urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:8791/api/status?key={key}", data=json.dumps(status).encode(), headers={"Content-Type": "application/json"}), timeout=10).read()
print("status posted:", len(STEPS), "steps;", sum(len(s.get("files", [])) for s in STEPS), "files")
