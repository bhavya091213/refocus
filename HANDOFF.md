# Refocus project: handoff (written 2026-11-06, ~01:15 UTC on the PC clock)

Class final project (user: **Bhavya**, Windows account "Raj"). Goal: one photo -> 9-frame focal stack -> click any pixel to refocus. Based on Tedla et al., *Learning to Refocus with Video Diffusion Models* (SIGGRAPH Asia 2025, https://learn2refocus.github.io/, code https://github.com/tedlasai/learn2refocus, arXiv 2512.19823). Repo: https://github.com/bhavya091213/refocus (main). **Always credit/cite the original work. Always include the dashboard link in replies** (see memory).

## State: everything requested is DONE except the arm-A re-run (running, unattended)

| Deliverable | Where | Status |
|---|---|---|
| Report (LaTeX, 16 pp, no TODOs) | `report/main.tex` -> `report/main.pdf`; compile: `cd report && ../tools/tectonic/tectonic.exe main.tex` | done; figures built by `scripts/make_report_figs.py` |
| 3-slide deck + speaker notes (3 min) | `slides/refocus_slides.pptx|pdf`, `speaker_notes.md`, `build.js` (node) | done |
| Click-to-refocus viewer | `viewer/` (static; `python -m http.server 8765`) | done; incl. "make a stack from your photo" card |
| Remotion animations | `remotion/src/*.tsx`, videos in `remotion/out/*.mp4` (All.mp4 = 50 s) | done (render needs `--browser-executable` = installed Chrome) |
| Dashboard (tabs: Overview, Results, Training, Cloud & hardware, Deliverables, Log) | `dashboard/server.py` + `index.html`, port 8791, Cloudflare quick tunnel | running on the PC |
| Results / ablation | `results/eval_*/metrics.json`, `scripts/build_dashboard_results.py` | done |

Dashboard: `https://demand-rising-tons-facts.trycloudflare.com/?key=<token in dashboard/token.txt>` (the quick-tunnel URL changes if cloudflared restarts: read `logs/tunnel.log`). Phone demo: `/v/<token>/` on the same host.

## Key results (20 held-out scenes x input positions 1,4,7 = 60 items per model; 4,000 training steps per arm)
Authors 200k: PSNR 31.07 / SSIM .893 / LPIPS .160 / depth-rho -0.70. A random 28.76/.870/.192/-0.61; B ablate_position 29.11/.863/.196/-0.58; C ablate_time 28.62/.858/.199/-0.61 (real stacks rho -0.76).
Paired (same items): B>C on all metrics (+0.49 dB, 55/60); A>C on SSIM/LPIPS; A vs B = PSNR (B) vs SSIM/LPIPS (A) trade-off. Table standard errors are over the 60 items (frame-level SEs in metrics.json are too small; don't use them).
Paper vs repo recipe: paper Sec. 5.1 says lr 4e-4, batch 4, EMA 1e-5, 200k iterations; repo defaults (what we ran) are lr 1e-5 x scale_lr, batch 1, no EMA. Mentioned in the report.
Measured params: U-Net 1,524.6 M, of which 397.6 M (26.1 %) temporal blocks trained; CLIP 632 M; VAE 97.7 M.

## Money (Lambda Cloud, key in `secrets/lambda.key`, gitignored; never print it)
- Spent: 8xA100 ablation $53.93 (3.39 h). A10 inference test ~1 h (~$1.5, terminated). A100 re-run in progress ($1.99/h, budget cap $20 via watchdog). Total project cap was $100.
- **Instance 12e2860b24724abaa0e5f975ecf38d0c** (1xA100, us-west-2, IP in `logs/new_ip.txt`) is **training arm A again** (`scripts/run_single_arm.sh`: 1 GPU x grad-accum 2, 4,000 steps, seed 0, then eval on the same 20x3 items). Started 00:54 UTC; ETA training ~04:40 UTC, eval ~05:55 UTC. Pipeline log on the box: `~/pipeline.log`; per-run logs `~/train_armA_rerun.log`.
- **Unattended finisher already running on the PC:** `scripts/finish_rerun.sh` (log `logs/finish_rerun.log`). When the pipeline logs ALL DONE it pulls `checkpoint-4000/unet` + `metrics.json` + sheets + train log into `checkpoints/armA_rerun/` (gitignored, ~6 GB), writes `PULLED_OK`, then terminates the instance. If it failed/pull is incomplete the instance is left for the watchdogs. `scripts/watchdog.py` (log `logs/watchdog.log`) kills the instance at `logs/deadline.txt` (~07:40 UTC) or $20.
- **If the PC was off/asleep and the finisher died:** check `curl .../instances` (see `scripts/watchdog.py` for the API call). If the instance still exists, run the finisher again; otherwise the run is lost (re-run `scripts/setup_new_instance.sh <ip>` then `run_single_arm.sh`, ~5 h).
- To avoid surprise bills: `python scripts/cloud_monitor.py` writes dashboard cloud card; terminate via `POST /instance-operations/terminate`.

## What the next agent should do when the re-run finishes
1. Confirm `checkpoints/armA_rerun/PULLED_OK` and instance `terminated`. Compare `metrics.json` to arm A (28.76/.870/.192/-0.61): this is a reproducibility check (same recipe, different seed handling/accumulation), add 1-2 sentences + a table row to `report/main.tex` (Results + Compute budget: add ~3.9 h train + 1.2 h eval + setup of $1.99/h, and the A10 hour), rebuild PDF, `python scripts/build_deliverables.py`, rebuild dashboard (`python -I scripts/build_dashboard_status.py`, `build_dashboard_results.py`), commit, push.
2. Optional: serve our own weights in the photo generator: `REFOCUS_UNET=<path to checkpoints/armA_rerun/unet>` in `scripts/infer_server.py` (needs a GPU box).
3. Update the Limitations text in the report (currently says the demo uses the authors' weights).

## Photo-to-stack generator (new image from the phone)
Flow: browser (viewer, `/v/<token>/`) -> `dashboard/server.py` (`POST /v/<token>/api/gen?pos=K`, `GET .../api/gen/<id>`, `.../gen/<id>/frame_i.jpg`, `.../api/backend`) -> SSH tunnel `localhost:8801` (`scripts/gpu_tunnel.sh`, uses `logs/infer_ip.txt`) -> `scripts/infer_server.py` on a GPU box (authors' checkpoint). It was verified end to end on a 24 GB A10 (fp32 weights + bf16 autocast, `decode_chunk_size=2` patched into `simple_inference.py` on the box, ~48 s per 576x832 image). **No GPU server is running now** (A10 terminated), so the page says "GPU server offline".
To bring it back: launch `gpu_1x_a10` (check `instance-types` capacity), put its IP in `logs/infer_ip.txt`, run `bash scripts/setup_infer_instance.sh <ip>` (installs env, starts server; ~15 min), start `scripts/gpu_tunnel.sh`, and start `scripts/watchdog_infer.py` (reads `logs/infer_instance_id.txt`, `infer_deadline.txt`; edit those first). Remember: `pkill -f` over ssh kills your own session; use `scripts/restart_infer_server.sh` (scp it to the box and run it).
Local PC (AMD RX 6900 XT 16 GB, 32 GB RAM, no CUDA) generation was being explored with offloading (user asked) in `local_infer/` (20 GB: venv + HF cache, gitignored) but the agent was stopped before reporting; treat as unfinished/untested. Delete `local_infer/` if disk space is needed.

## Environment gotchas
- Shell heredocs mangle backslashes: write LaTeX/Python with the Write tool or script files. Windows `python` for repo scripts: use `-I`; Playwright venv: `.venv-pw/Scripts/python.exe`.
- `git add -A` once swept in 17k files of `local_infer/` (undone before push). `.gitignore` now excludes `local_infer/`, `checkpoints/`, `dashboard/gen/`, logs, secrets. Check `git status --short | head` before committing.
- PawnIO driver for CPU temperatures on the dashboard NOT installed (needs user approval).
- Dataset licence is not stated; do not redistribute (data/ is gitignored).
- Background processes on the PC (keep running): dashboard server (8791), cloudflared tunnel, cloud_monitor.py, watchdog.py, finish_rerun.sh, sys_monitor. Stop them with Task Manager / `taskkill` when the project is over.
