"""Record a looping demo GIF (and optional MP4) of the click-to-refocus viewer.

Drives the REAL viewer page (viewer/index.html + app.js, unmodified) in the installed
Google Chrome via Playwright, with a virtual clock so every frame is deterministic.
The clicks are real mouse clicks on the page, so app.js's own sharpness logic picks the
frame. The recorder only re-arranges the page into a compact portrait stage at runtime
and layers on a cursor, a click ripple, captions and a credit line.

Storyboard: (1) the input photo alone, (2) step through the 9-frame stack,
(3) cursor clicks each --clicks point and the viewer refocuses there; loops back to (1).

Usage (needs ffmpeg on PATH and the playwright package; Chrome must be installed):
  uv run --with playwright python scripts/make_demo_gif.py \
      --stack blender_macro --input-pos 4 --clicks "0.38,0.44 0.78,0.22" \
      --credit "stack generated from one photo by ..." --out demo.gif [--mp4]

Click points are fractions of the image width,height (0..1). Intermediate PNG frames go
to --workdir (default: <out without .gif>_frames next to the output).
"""
import argparse, json, math, shutil, socket, subprocess, sys, time, urllib.request
from pathlib import Path

VIEWER = Path(__file__).resolve().parent.parent / "viewer"
STAGE_W = 500          # CSS px of the recording stage; rendered at 2x then scaled to --width
IMG_W = 300            # CSS px of the image column (height follows the stack aspect ratio)
CAPTIONS = ["One input photo", "The model generates a 9-frame focal stack", "Click anywhere to refocus"]
DIM = 0.12             # opacity of not-yet-shown strip thumbnails

CSS = """
body{margin:0;width:%(W)dpx;background:#0f1115}
body>header,body>main,body>footer,#hint{display:none!important}
#rec{position:relative;width:%(W)dpx;padding:10px 12px 12px;background:#0f1115;overflow:hidden}
#recCap{display:flex;align-items:center;gap:10px;min-height:60px;font:700 23px/1.2 system-ui,sans-serif;color:#fff}
#recCap b{flex:none;width:34px;height:34px;border-radius:50%%;background:#ff9a3c;color:#111;display:grid;place-items:center;font-size:20px}
#recRow{display:grid;grid-template-columns:%(IW)dpx 1fr;gap:12px;margin-top:6px}
#recSide{display:flex;flex-direction:column;gap:6px;min-width:0}
#recSide h2{margin:4px 0 0;font-size:12px}
#recSide .big{font-size:64px}
#recSide .big small{font-size:20px}
#recSide .sliderRow{margin-top:2px;font-size:12px;gap:6px}
#recSide .sliderRow input{min-width:0}
#recPlotHint{margin:30px 0 0;font-size:12px;color:#6b7383;text-align:center}
#recLegend{font-size:12px;color:#9aa3b2;line-height:1.3}
#recLegend i{color:#ff9a3c;font-style:normal;font-weight:700}
#rec .strip{margin-top:8px}
#rec .strip button span{font-size:12px}
#rec .canvasWrap{cursor:none}
#recCredit{margin-top:8px;font-size:12.5px;line-height:1.35;color:#9aa3b2}
#recCursor{position:absolute;left:0;top:0;width:30px;height:30px;pointer-events:none;z-index:20;transform-origin:3px 2px}
#recRipple{position:absolute;border:3px solid #ff9a3c;border-radius:50%%;pointer-events:none;z-index:19;box-shadow:0 0 0 2px rgba(0,0,0,.35)}
"""

SETUP_JS = """([css, credit, side, plotH]) => {
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  const $ = id => document.getElementById(id);
  const rec = document.createElement('div'); rec.id = 'rec';
  rec.innerHTML = `<div id="recCap"><b></b><span></span></div>
    <div id="recRow"><div id="recImg"></div><div id="recSide">
      <h2>Focus position</h2><div id="recBig"></div><div id="recSlider"></div>
      <h2>Sharpness at click</h2><div id="recPlot"><p id="recPlotHint">(measured when you click)</p></div>
      <div id="recLegend"><i>orange</i> = sharpest frame, picked by the viewer</div></div></div>
    <div id="recStrip"></div><div id="recCredit"></div>
    <div id="recRipple" hidden></div>
    <svg id="recCursor" viewBox="0 0 24 24"><path d="M3 2 L3 19 L7.5 15 L10.5 22 L13.5 20.8 L10.6 14 L16.5 14 Z"
      fill="#fff" stroke="#000" stroke-width="1.4" stroke-linejoin="round"/></svg>`;
  document.body.appendChild(rec);
  $('recImg').appendChild($('wrap')); $('recBig').appendChild(document.querySelector('.big'));
  $('recSlider').appendChild(document.querySelector('.sliderRow')); $('recStrip').appendChild($('strip'));
  const plot = $('plot'); plot.width = side; plot.height = plotH; $('recPlot').appendChild(plot);
  $('recCredit').textContent = credit; $('recCredit').hidden = !credit;
  window.__rec = s => {
    $('recCap').querySelector('b').textContent = s.cap; $('recCap').querySelector('span').textContent = s.capText;
    const c = $('recCursor'); c.style.opacity = s.cur[2];
    c.style.transform = `translate(${s.cur[0] - 3}px, ${s.cur[1] - 2}px) scale(${s.cur[3]})`;
    const r = $('recRipple'); r.hidden = !s.rip;
    if (s.rip) { const [x, y, rad, op] = s.rip; Object.assign(r.style, { left: x - rad + 'px', top: y - rad + 'px',
      width: 2 * rad + 'px', height: 2 * rad + 'px', opacity: op }); }
    [...$('strip').children].forEach((b, i) => b.style.opacity = s.thumbs[i]);
    plot.style.opacity = s.plot; $('recPlotHint').hidden = !s.hint; plot.hidden = s.hint;
  };
  const rr = rec.getBoundingClientRect(), vr = $('view').getBoundingClientRect();
  return { w: rr.width, h: Math.ceil(rr.height), img: [vr.left - rr.left, vr.top - rr.top, vr.width, vr.height] };
}"""


def die(msg):
    print("make_demo_gif: error: " + msg, file=sys.stderr)
    sys.exit(1)


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stack", required=True, help="stack name under viewer/stacks (listed in index.json)")
    ap.add_argument("--input-pos", type=int, required=True, help="focus position (0-8) of the input photo")
    ap.add_argument("--clicks", required=True, help='click points "fx,fy fx,fy ..." as fractions of image w,h (1-3)')
    ap.add_argument("--credit", default="", help="small persistent footer line")
    ap.add_argument("--out", required=True, help="output .gif path")
    ap.add_argument("--width", type=int, default=540, help="output width in px (default 540)")
    ap.add_argument("--fps", type=int, default=12, help="frames per second (default 12)")
    ap.add_argument("--mp4", action="store_true", help="also write an H.264 MP4 next to the GIF")
    ap.add_argument("--workdir", help="where intermediate PNG frames go (default <out>_frames)")
    a = ap.parse_args()
    if not 0 <= a.input_pos <= 8:
        die("--input-pos must be 0..8")
    try:
        a.points = [tuple(float(v) for v in p.split(",")) for p in a.clicks.split()]
    except ValueError:
        die(f"cannot parse --clicks {a.clicks!r}; expected e.g. \"0.3,0.4 0.7,0.2\"")
    if not 1 <= len(a.points) <= 3 or any(len(p) != 2 or not all(0 <= v <= 1 for v in p) for p in a.points):
        die("--clicks needs 1-3 points 'fx,fy' with values in 0..1")
    if not 6 <= a.fps <= 30 or a.width < 200:
        die("--fps must be 6..30 and --width >= 200")
    return a


def find_stack(name):
    try:
        stacks = json.loads((VIEWER / "stacks" / "index.json").read_text())
    except (OSError, ValueError) as e:
        die(f"cannot read viewer/stacks/index.json: {e}")
    idx = next((i for i, s in enumerate(stacks) if s.get("name") == name), None)
    if idx is None:
        die(f"stack {name!r} is not in viewer/stacks/index.json (have: {', '.join(s.get('name', '?') for s in stacks)})")
    missing = [f for f in stacks[idx]["frames"] if not (VIEWER / f).is_file()]
    if len(stacks[idx]["frames"]) != 9 or missing:
        die(f"stack {name!r} needs 9 frame files; missing: {missing or 'wrong frame count'}")
    return idx


def start_server():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                             "--directory", str(VIEWER)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/"
    for _ in range(50):
        try:
            urllib.request.urlopen(url + "stacks/index.json", timeout=1).read(); return proc, url
        except OSError:
            if proc.poll() is not None: break
            time.sleep(0.1)
    proc.terminate(); die("could not start the local http server")


def ease(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def record(a, url, stack_idx, frames_dir):
    try:
        from playwright.sync_api import sync_playwright, Error as PWError
    except ImportError:
        die("playwright is not installed; run with `uv run --with playwright python ...`")
    errors = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except PWError as e:
            die(f"Google Chrome not found or failed to start ({str(e).splitlines()[0]})")
        try:
            page = browser.new_page(viewport={"width": STAGE_W, "height": 1400}, device_scale_factor=2)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.clock.install()
            page.goto(url)
            poll(page, "document.querySelectorAll('#stackSel option').length > 0", "stack list", errors)
            page.select_option("#stackSel", value=str(stack_idx))
            name = a.stack
            poll(page, f"[...document.querySelectorAll('#strip img')].length === 9 && "
                       f"[...document.querySelectorAll('#strip img')].every(i => i.src.includes('/{name}/') && i.complete)",
                 "stack frames", errors)
            page.clock.run_for(500)
            side = STAGE_W - 24 - IMG_W - 12
            geo = page.evaluate(SETUP_JS, [CSS % {"W": STAGE_W, "IW": IMG_W}, a.credit, side, 132])
            page.set_viewport_size({"width": STAGE_W, "height": geo["h"]})
            chosen = run_storyboard(page, a, geo, frames_dir)
            if errors:
                die("page error: " + "; ".join(errors))
            return chosen, geo
        finally:
            browser.close()


def poll(page, expr, what, errors, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if errors:
            die("page error while waiting for " + what + ": " + "; ".join(errors))
        if page.evaluate(expr):
            return
        time.sleep(0.1)
    about = page.evaluate("(document.getElementById('about') || {}).textContent || ''")
    die(f"timed out waiting for {what} (viewer says: {about!r})")


def run_storyboard(page, a, geo, frames_dir):
    fps, dt, inp = a.fps, 1000.0 / a.fps, a.input_pos
    n = lambda sec: max(1, round(sec * fps))
    ix, iy, iw, ih = geo["img"]
    pts = [(ix + fx * iw, iy + fy * ih) for fx, fy in a.points]
    count = [0]
    state = {"cap": "1", "capText": CAPTIONS[0], "cur": [0, 0, 0, 1], "rip": None,
             "thumbs": [1 if i == inp else DIM for i in range(9)], "plot": 1, "hint": True}

    def tick(**kw):
        state.update(kw)
        page.evaluate("s => window.__rec(s)", state)
        page.screenshot(path=str(frames_dir / f"f_{count[0]:04d}.png"), clip={"x": 0, "y": 0, "width": geo["w"], "height": geo["h"]})
        count[0] += 1
        page.clock.run_for(dt)

    def show(k):  # the strip's own buttons call the viewer's show(k)
        page.evaluate(f"document.querySelectorAll('#strip button')[{k}].click()")

    show(inp); page.clock.run_for(400)
    for _ in range(n(1.4)):                                   # 1. input photo only
        tick()
    steps = n(2.6); last = -1                                 # 2. step through the stack
    for j in range(steps):
        k = min(8, j * 9 // steps)
        if k != last:
            show(k); last = k
        tick(cap="2", capText=CAPTIONS[1], thumbs=[1 if i <= k or i == inp else DIM for i in range(9)])
    cur = (ix + iw * 0.92, iy + ih * 0.97)                    # 3. click to refocus
    for f in range(n(0.4)):
        tick(cap="3", capText=CAPTIONS[2], cur=[cur[0], cur[1], (f + 1) / n(0.4), 1])
    chosen = []
    for (px, py) in pts:
        g = n(0.65)
        for f in range(g):
            t = ease((f + 1) / g)
            tick(cur=[cur[0] + (px - cur[0]) * t, cur[1] + (py - cur[1]) * t, 1, 1], rip=None)
        cur = (px, py)
        page.mouse.click(px, py)       # #rec sits at the page origin; real click -> app.js picks the frame
        chosen.append(int(page.inner_text("#posNum")))
        for f in range(n(1.35)):
            t = f / fps
            rip = [px, py, 6 + 40 * min(1, t / 0.5), max(0, 1 - t / 0.5)] if t < 0.5 else None
            tick(cur=[px, py, 1, 0.82 if t < 0.12 else 1], rip=rip, hint=False)
    show(inp); page.evaluate("document.getElementById('cross').hidden = true")
    tail = n(0.6)                                             # back to the input photo, loops cleanly
    for f in range(tail):
        u = (f + 1) / tail
        tick(cur=[cur[0], cur[1], 1 - u, 1], rip=None, plot=1 - u,
             thumbs=[1 if i == inp else 1 - (1 - DIM) * u for i in range(9)])
    page.evaluate("(() => { const p = document.getElementById('plot'); p.getContext('2d').clearRect(0, 0, p.width, p.height); })()")
    return chosen, count[0]


def encode(a, frames_dir, nframes):
    src = ["-framerate", str(a.fps), "-i", str(frames_dir / "f_%04d.png")]
    scale = f"scale={a.width}:-2:flags=lanczos"
    pal = frames_dir / "palette.png"
    run(["ffmpeg", "-y", "-v", "error", *src, "-frames:v", str(nframes), "-vf",
         f"{scale},palettegen=max_colors=256:stats_mode=full", "-update", "1", str(pal)])
    run(["ffmpeg", "-y", "-v", "error", *src, "-i", str(pal), "-frames:v", str(nframes), "-lavfi",
         f"[0:v]{scale}[x];[x][1:v]paletteuse=dither=sierra2_4a", "-loop", "0", str(a.out)])
    if a.mp4:
        run(["ffmpeg", "-y", "-v", "error", *src, "-frames:v", str(nframes), "-vf", scale, "-c:v", "libx264",
             "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", str(Path(a.out).with_suffix(".mp4"))])


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        die(f"{cmd[0]} failed: {r.stderr.strip()[-800:]}")


def main():
    a = parse_args()
    a.out = Path(a.out).expanduser().resolve()
    if a.out.suffix.lower() != ".gif":
        die("--out must end in .gif")
    if not shutil.which("ffmpeg"):  # checked before recording, so a missing encoder fails fast
        die("ffmpeg not found on PATH")
    stack_idx = find_stack(a.stack)
    frames_dir = Path(a.workdir).expanduser().resolve() if a.workdir else a.out.with_name(a.out.stem + "_frames")
    frames_dir.mkdir(parents=True, exist_ok=True); a.out.parent.mkdir(parents=True, exist_ok=True)
    server, url = start_server()
    try:
        (chosen, nframes), geo = record(a, url, stack_idx, frames_dir)
    finally:
        server.terminate(); server.wait()
    encode(a, frames_dir, nframes)
    h = round(geo["h"] * a.width / geo["w"] / 2) * 2
    print(f"clicks {a.clicks} -> viewer chose frames {chosen}")
    print(f"wrote {a.out}  {a.width}x{h}px  {nframes} frames @ {a.fps} fps = {nframes / a.fps:.1f}s  "
          f"{a.out.stat().st_size / 1e6:.2f} MB" + ("  (+ .mp4)" if a.mp4 else ""))


if __name__ == "__main__":
    main()
