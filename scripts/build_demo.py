"""Build everything the demo slide shows from one viewer stack.

Runs scripts/make_demo_gif.py (which drives the real viewer), reads back which frame the
viewer chose for each click, and writes:
  slides/demo.gif                the recording
  slides/demo/frame_0..8.jpg     the nine frames of the stack
  slides/demo/click_N_before.jpg a close-up around click N in the input photo
  slides/demo/click_N_after.jpg  the same close-up in the frame the viewer chose
  slides/demo/demo.json          what slides/slide3.js and slides/notes.js read

usage:
  python scripts/build_demo.py --stack NAME --input-pos K --clicks "fx,fy fx,fy" \
      --labels "the near pawn|the far rook" --model "our fine-tuned model (...)" [--workdir DIR]
Needs pillow and playwright in the interpreter that runs it, plus ffmpeg and Chrome.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "slides" / "demo"
RING = (242, 163, 58)  # the deck's amber
CROP = 0.36  # close-up side as a fraction of the frame width
CLOSEUP_PX = 480


def fail(msg: str) -> None:
    sys.exit("build_demo: " + msg)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--stack", required=True, help="name under viewer/stacks")
    p.add_argument("--input-pos", type=int, required=True)
    p.add_argument("--clicks", required=True, help='"fx,fy fx,fy" as fractions of width and height')
    p.add_argument("--labels", required=True, help="one label per click, separated by |")
    p.add_argument("--model", required=True, help="what generated the stack, as shown on the slide")
    p.add_argument("--workdir", default=None, help="where the recorder keeps its PNG frames")
    a = p.parse_args()
    a.points = [tuple(float(v) for v in pt.split(",")) for pt in a.clicks.split()]
    a.label_list = [s.strip() for s in a.labels.split("|")]
    if len(a.points) != len(a.label_list):
        fail("--labels needs exactly one label per click")
    return a


def record(a: argparse.Namespace) -> list[int]:
    """Runs the recorder and returns the frame the viewer chose for each click."""
    workdir = a.workdir or tempfile.mkdtemp(prefix="refocus_demo_")
    credit = "Stack generated from one photo by %s. Method: Tedla et al., SIGGRAPH Asia 2025" % a.model
    cmd = [sys.executable, str(ROOT / "scripts" / "make_demo_gif.py"), "--stack", a.stack,
           "--input-pos", str(a.input_pos), "--clicks", a.clicks, "--credit", credit,
           "--out", str(ROOT / "slides" / "demo.gif"), "--workdir", workdir]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        fail("recorder failed: " + (done.stderr or done.stdout).strip()[-600:])
    match = re.search(r"viewer chose frames \[([0-9, ]*)\]", done.stdout)
    if not match:
        fail("could not read the chosen frames from the recorder output: " + done.stdout[-300:])
    chosen = [int(v) for v in match.group(1).split(",") if v.strip()]
    if len(chosen) != len(a.points):
        fail("recorder reported %d frames for %d clicks" % (len(chosen), len(a.points)))
    return chosen


def save(im: Image.Image, path: Path, width: int) -> None:
    height = round(im.height * width / im.width)
    im.resize((width, height), Image.LANCZOS).save(path, quality=92)


def crop_box(im: Image.Image, fx: float, fy: float) -> tuple[int, int, int, int]:
    """A square close-up around the click (CROP of the frame width), kept inside the image."""
    side = round(im.width * CROP)
    left = min(max(round(fx * im.width - side / 2), 0), im.width - side)
    top = min(max(round(fy * im.height - side / 2), 0), im.height - side)
    return left, top, left + side, top + side


def closeup(im: Image.Image, fx: float, fy: float, box: tuple[int, int, int, int]) -> Image.Image:
    """The close-up, enlarged, with a small ring where the click landed."""
    scale = CLOSEUP_PX / (box[2] - box[0])
    out = im.crop(box).resize((CLOSEUP_PX, CLOSEUP_PX), Image.LANCZOS)
    draw = ImageDraw.Draw(out)
    x, y, r = (fx * im.width - box[0]) * scale, (fy * im.height - box[1]) * scale, CLOSEUP_PX // 14
    for k in range(4):
        draw.ellipse([x - r - k, y - r - k, x + r + k, y + r + k], outline=RING)
    return out


def main() -> None:
    a = parse_args()
    stack_dir = ROOT / "viewer" / "stacks" / a.stack
    paths = [stack_dir / ("frame_%d.jpg" % i) for i in range(9)]
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        fail("stack %s is missing %s" % (a.stack, ", ".join(missing)))
    chosen = record(a)
    frames = [Image.open(p).convert("RGB") for p in paths]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for i, frame in enumerate(frames):
        save(frame, OUT_DIR / ("frame_%d.jpg" % i), 320)
    clicks = []
    for n, ((fx, fy), frame_idx, label) in enumerate(zip(a.points, chosen, a.label_list), start=1):
        box = crop_box(frames[0], fx, fy)
        before, after = "click_%d_before.jpg" % n, "click_%d_after.jpg" % n
        closeup(frames[a.input_pos], fx, fy, box).save(OUT_DIR / before, quality=92)
        closeup(frames[frame_idx], fx, fy, box).save(OUT_DIR / after, quality=92)
        clicks.append({"x": fx, "y": fy, "frame": frame_idx, "label": label, "before": before, "after": after})
    meta = {"stack": a.stack, "input_pos": a.input_pos, "model": a.model, "clicks": clicks,
            "frame_size": [frames[0].width, frames[0].height]}
    (OUT_DIR / "demo.json").write_text(json.dumps(meta, indent=1) + "\n")
    sys.stdout.write("demo built from %s: clicks -> frames %s\n" % (a.stack, chosen))


if __name__ == "__main__":
    main()
