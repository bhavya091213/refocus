"""GPU inference server for the click-to-refocus demo. Runs on the Lambda instance (127.0.0.1:8801, reached from the PC through an ssh tunnel).
POST /gen?pos=K   body = raw image bytes  ->  JSON {"frames": [9 base64 jpegs], "size": [w, h], "seconds": s}
GET  /health      -> {"ok": true, "ckpt": ...}
One job at a time (lock). Model: authors' released checkpoint by default; set REFOCUS_UNET to a local unet folder to use our own fine-tuned weights.
Env: REFOCUS_DTYPE=fp32|bf16 weights (default fp32 weights + bf16 autocast, which fits a 24 GB GPU), REFOCUS_AUTOCAST=1, REFOCUS_MAXPIX (default 500000)."""
import base64, io, json, math, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import numpy as np, torch
from PIL import Image
sys.path.insert(0, os.getcwd())
import simple_inference as si
from simple_pipeline import StableVideoDiffusionPipeline
from transformers import CLIPVisionModelWithProjection
from diffusers import AutoencoderKLTemporalDecoder, UNetSpatioTemporalConditionModel

DT = torch.bfloat16 if os.environ.get("REFOCUS_DTYPE", "fp32") == "bf16" else torch.float32
AUTOCAST = os.environ.get("REFOCUS_AUTOCAST", "1") == "1"
MAXPIX = int(os.environ.get("REFOCUS_MAXPIX", "500000"))
UNET = os.environ.get("REFOCUS_UNET", "")
def find_scale(h, w):
    s = 1.0
    while True:
        sh, sw = math.floor(h * s / 64) * 64, math.floor(w * s / 64) * 64
        if sh * sw <= MAXPIX: return sh, sw
        s -= 0.01
si.find_scale = find_scale
dev = torch.device("cuda")
SVD = "stabilityai/stable-video-diffusion-img2vid"
enc = CLIPVisionModelWithProjection.from_pretrained(SVD, subfolder="image_encoder").requires_grad_(False).to(dev, dtype=DT).eval()
vae = AutoencoderKLTemporalDecoder.from_pretrained(SVD, subfolder="vae", variant="fp16").requires_grad_(False).to(dev, dtype=DT).eval()
if UNET: unet = UNetSpatioTemporalConditionModel.from_pretrained(UNET)
else: unet = UNetSpatioTemporalConditionModel.from_pretrained("tedlasai/learn2refocus", subfolder="checkpoint-200000/unet")
unet = unet.to(dev, dtype=DT).eval()
pipe = StableVideoDiffusionPipeline.from_pretrained(SVD, unet=unet, image_encoder=enc, vae=vae, torch_dtype=DT)
print("model loaded", DT, MAXPIX, UNET or "authors-200k", "vram", torch.cuda.memory_allocated() / 2**30, flush=True)
LOCK = threading.Lock()

class A:  # args stand-in for simple_inference.inference_on_image
    num_inference_steps = 25

def generate(img_bytes, pos):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    if max(w, h) > 2400: img.thumbnail((2400, 2400))
    batch = si.convert_to_batch(img, input_focal_position=pos)
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=AUTOCAST):
        frames, _ = si.inference_on_image(A, batch, pipe, dev)
    frames = frames.float().clamp(0, 1)
    out = []
    for i in range(9):
        im = Image.fromarray((frames[i].permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)); b = io.BytesIO(); im.save(b, "JPEG", quality=92); out.append(base64.b64encode(b.getvalue()).decode())
    torch.cuda.empty_cache()
    return out, list(im.size)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, code, d):
        b = json.dumps(d).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if urlparse(self.path).path == "/health": return self._j(200, {"ok": True, "ckpt": UNET or "authors-200k", "dtype": str(DT), "busy": LOCK.locked()})
        self._j(404, {"error": "nf"})
    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/gen": return self._j(404, {"error": "nf"})
        pos = int((parse_qs(u.query).get("pos") or ["4"])[0]); pos = min(8, max(0, pos))
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        t = time.time()
        with LOCK:
            try:
                frames, size = generate(raw, pos)
            except Exception as e:
                torch.cuda.empty_cache(); import traceback; traceback.print_exc(); print("ERR", repr(e), flush=True); return self._j(500, {"error": repr(e)[:300]})
        print("job done", round(time.time() - t, 1), "s", flush=True)
        self._j(200, {"frames": frames, "size": size, "seconds": round(time.time() - t, 1)})

ThreadingHTTPServer(("127.0.0.1", 8801), H).serve_forever()
