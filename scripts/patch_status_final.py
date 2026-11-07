import io
p = "D:/Refocus/scripts/build_dashboard_status.py"
s = io.open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"; s = s.replace("\r\n", "\n")
def rep(a, b):
    global s
    assert a in s, a[:70]
    s = s.replace(a, b, 1)
rep('title="Fine-tune the 3 arms on 8x A100 (parallel) + evaluate", state="doing", note="instance setup in progress; training starts when ready"',
    'title="Fine-tune the 3 arms on 8x A100 (parallel) + evaluate", state="done", note="4,000 steps each in 1h58m · all evals done · instance terminated · 3.39 h = $53.93"')
rep('"Loss curves per run stream into the chart above; per-GPU metadata is in \'GPU details\'.",',
    '"RESULT: authors 200k PSNR 31.07 / SSIM .893 / LPIPS .160; A random 28.76 / .870 / .192; B ablate_position 29.11 / .863 / .196; C ablate_time 28.62 / .858 / .199. Paired over the same 60 items: B beats C on all metrics (PSNR +0.49 dB, 55/60 items); A beats C on SSIM/LPIPS; A vs B is a PSNR (B) vs SSIM/LPIPS (A) trade-off. Full tables and charts: Results tab.\\n"\n            "COST: launched 19:24 UTC, terminated 22:48 UTC = 3.39 h x $15.92/h = $53.93 of the $100 cap. The 25 GB checkpoints per arm were not downloaded (instance terminated), so the demo uses the authors\' weights.",')
rep('title="Blender demo scenes (CC0 assets) -> model", state="doing", note="renders done · inference running"', 'title="Blender demo scenes (CC0 assets) -> model", state="done", note="3 scenes rendered · authors\' model gives plausible near-to-far sweep, 1-3 position errors"')
rep('title="Extra credit: depth mapping and focus", state="doing"', 'title="Extra credit: depth mapping and focus", state="done"')
rep('title="Metrics on a test subset", state="todo", note="PSNR · SSIM · LPIPS · FID · VIF"', 'title="Metrics on a test subset", state="done", note="PSNR · SSIM · LPIPS · depth-consistency on 20 scenes x 3 input positions x 4 models (FID/VIF not run)"')
rep('title="Click-to-refocus demo + Remotion animations", state="todo", note="sharpness data computed from real frames"', 'title="Click-to-refocus demo + Remotion animations", state="done", note="viewer/ (8 sample stacks) · remotion/ scenes rendered"')
rep('"Remotion project scaffolded in D:\\\\Refocus\\\\remotion (sample frames + real sharpness data ready); animation scenes still to be written.",', '"Viewer: D:\\\\Refocus\\\\viewer (static web app: click picks sharpest frame, sharpness-vs-position plot, depth-like map, upload 9 frames). Remotion animations: D:\\\\Refocus\\\\remotion. See the Deliverables tab.",')
rep('title="Report (LaTeX) + 3 slides", state="doing", note="architecture + data sections written"', 'title="Report (LaTeX) + 3 slides", state="done", note="full report incl. results, paired analysis, limitations · 3-slide deck"')
rep('Placeholders (red TBD) for results. Slides: 3 slides / 3 minutes not started.', 'Results, paired-comparison analysis, compute budget, limitations and conclusion are written. 3-slide / 3-minute deck is in D:\\\\Refocus\\\\slides.')
rep('["Phase", "Blender demo + training plan"], ["Base model", "SVD img2vid"], ["Train / test scenes", "1474 / 164"], ["Cloud", "1x A100 40GB, $1.99/hr"],\n                 ["Train speed", "1.71 s/step (bf16)"], ["Ablation", "not chosen yet"]]',
    '["Phase", "Finished: results in, deliverables built"], ["Base model", "SVD img2vid"], ["Train / test scenes", "1474 / 164"], ["Cloud", "terminated · $53.93 of $100"],\n                 ["Best of ours", "A random (SSIM/LPIPS) / B ablate_position (PSNR)"], ["Authors\' 200k", "PSNR 31.07 · LPIPS 0.160"]]')
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl)); print("ok")
