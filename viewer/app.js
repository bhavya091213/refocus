// Click-to-refocus viewer: dependency-free. Sharpness = variance of the Laplacian in a window, from integral images.
"use strict";
const $ = id => document.getElementById(id);
const view = $("view"), vctx = view.getContext("2d");
const depthC = $("depth"), dctx = depthC.getContext("2d");
const wrap = $("wrap"), cross = $("cross"), slider = $("slider"), strip = $("strip");
const plot = $("plot"), pctx = plot.getContext("2d");

let S = null;           // current stack: {imgs[9], w, h, aw, ah, I1[9], I2[9], rad, depthIdx, title, note}
let cur = 0;            // frame currently shown (target)
let anim = null;        // crossfade animation state
let stacks = [];

// ---------- loading ----------
function loadImg(src) {
  return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("failed to load " + src)); im.src = src; });
}

// Integral images of Laplacian and Laplacian^2 at analysis resolution (width <= 256).
function analyse(imgs) {
  const w = imgs[0].naturalWidth, h = imgs[0].naturalHeight;
  const sc = Math.min(1, 256 / w), aw = Math.max(8, Math.round(w * sc)), ah = Math.max(8, Math.round(h * sc));
  const c = document.createElement("canvas"); c.width = aw; c.height = ah;
  const g = c.getContext("2d", { willReadFrequently: true });
  const I1 = [], I2 = [], stride = aw + 1;
  for (const im of imgs) {
    g.drawImage(im, 0, 0, aw, ah);
    const d = g.getImageData(0, 0, aw, ah).data, gray = new Float32Array(aw * ah);
    for (let i = 0; i < aw * ah; i++) gray[i] = 0.299 * d[4 * i] + 0.587 * d[4 * i + 1] + 0.114 * d[4 * i + 2];
    const a = new Float64Array(stride * (ah + 1)), b = new Float64Array(stride * (ah + 1));
    for (let y = 0; y < ah; y++) {
      let r1 = 0, r2 = 0;
      for (let x = 0; x < aw; x++) {
        const xm = Math.max(0, x - 1), xp = Math.min(aw - 1, x + 1), ym = Math.max(0, y - 1), yp = Math.min(ah - 1, y + 1);
        const L = gray[y * aw + xm] + gray[y * aw + xp] + gray[ym * aw + x] + gray[yp * aw + x] - 4 * gray[y * aw + x];
        r1 += L; r2 += L * L;
        a[(y + 1) * stride + x + 1] = a[y * stride + x + 1] + r1;
        b[(y + 1) * stride + x + 1] = b[y * stride + x + 1] + r2;
      }
    }
    I1.push(a); I2.push(b);
  }
  return { w, h, aw, ah, I1, I2, stride, rad: Math.max(3, Math.round(0.05 * aw)) };
}

// variance of the Laplacian in a (2r+1)^2 window centred at analysis coords (x, y), for frame k
function sharp(k, x, y, r) {
  const { aw, ah, I1, I2, stride } = S;
  const x0 = Math.max(0, x - r), x1 = Math.min(aw, x + r + 1), y0 = Math.max(0, y - r), y1 = Math.min(ah, y + r + 1);
  const n = (x1 - x0) * (y1 - y0);
  const box = A => A[y1 * stride + x1] - A[y0 * stride + x1] - A[y1 * stride + x0] + A[y0 * stride + x0];
  const m = box(I1[k]) / n;
  return box(I2[k]) / n - m * m;
}
const curve = (x, y, r = S.rad) => Array.from({ length: 9 }, (_, k) => sharp(k, x, y, r));
const argmax = a => a.reduce((b, v, i) => (v > a[b] ? i : b), 0);

// depth-like map: per coarse cell, argmax frame (cells need some texture, otherwise left grey)
function buildDepth() {
  const gx = 32, gy = Math.max(4, Math.round(gx * S.ah / S.aw));
  const idx = new Int8Array(gx * gy), r = Math.max(3, Math.round(S.aw / gx));
  for (let j = 0; j < gy; j++) for (let i = 0; i < gx; i++) {
    const c = curve(Math.round((i + .5) * S.aw / gx), Math.round((j + .5) * S.ah / gy), r);
    const mx = Math.max(...c), mn = Math.min(...c);
    idx[j * gx + i] = mx < 1 || mx < 1.15 * mn ? -1 : argmax(c);
  }
  S.depthIdx = { idx, gx, gy };
  depthC.width = S.w; depthC.height = S.h;
  dctx.clearRect(0, 0, S.w, S.h);
  const cw = S.w / gx, ch = S.h / gy;
  for (let j = 0; j < gy; j++) for (let i = 0; i < gx; i++) {
    const v = idx[j * gx + i];
    dctx.fillStyle = v < 0 ? "rgba(120,120,120,.45)" : colormap(v / 8);
    dctx.fillRect(Math.floor(i * cw), Math.floor(j * ch), Math.ceil(cw) + 1, Math.ceil(ch) + 1);
  }
}
function colormap(t) { // near (0) warm -> far (1) cool
  const s = [[255, 120, 40], [255, 214, 70], [90, 210, 130], [60, 150, 230], [110, 80, 220]];
  const p = t * (s.length - 1), i = Math.min(s.length - 2, Math.floor(p)), f = p - i;
  return `rgb(${s[i].map((c, k) => Math.round(c + (s[i + 1][k] - c) * f)).join(",")})`;
}

// ---------- drawing / animation ----------
function drawFrame(i) { vctx.globalAlpha = 1; vctx.drawImage(S.imgs[i], 0, 0, view.width, view.height); }
function show(to) {
  to = Math.max(0, Math.min(8, to));
  const from = cur; cur = to; slider.value = to;
  $("posNum").textContent = to;
  [...strip.children].forEach((b, i) => b.classList.toggle("on", i === to));
  if (anim) cancelAnimationFrame(anim.raf);
  if (from === to) { drawFrame(to); return; }
  const t0 = performance.now(), dur = 280, hold = anim ? anim.from : from;
  anim = { from: hold, raf: 0 };
  const step = now => {
    const t = Math.min(1, (now - t0) / dur);
    drawFrame(hold); vctx.globalAlpha = t; vctx.drawImage(S.imgs[to], 0, 0, view.width, view.height); vctx.globalAlpha = 1;
    if (t < 1) anim.raf = requestAnimationFrame(step); else anim = null;
  };
  anim.raf = requestAnimationFrame(step);
}

function drawPlot(c, best) {
  const W = plot.width, H = plot.height, pad = { l: 8, r: 8, t: 10, b: 24 };
  pctx.clearRect(0, 0, W, H);
  const mx = Math.max(...c) || 1, bw = (W - pad.l - pad.r) / 9;
  pctx.strokeStyle = "#2a2f3a"; pctx.beginPath(); pctx.moveTo(pad.l, H - pad.b + .5); pctx.lineTo(W - pad.r, H - pad.b + .5); pctx.stroke();
  c.forEach((v, k) => {
    const h = Math.max(1, (v / mx) * (H - pad.t - pad.b)), x = pad.l + k * bw + 3;
    pctx.fillStyle = k === best ? "#ff9a3c" : "#4a5a78"; pctx.fillRect(x, H - pad.b - h, bw - 6, h);
    pctx.fillStyle = k === best ? "#ff9a3c" : "#9aa3b2"; pctx.font = "12px system-ui"; pctx.textAlign = "center"; pctx.fillText(k, x + (bw - 6) / 2, H - 8);
  });
  pctx.strokeStyle = "#e8eaf0"; pctx.lineWidth = 1.5; pctx.beginPath();
  c.forEach((v, k) => { const x = pad.l + k * bw + bw / 2, y = H - pad.b - (v / mx) * (H - pad.t - pad.b); k ? pctx.lineTo(x, y) : pctx.moveTo(x, y); });
  pctx.stroke(); pctx.lineWidth = 1;
}

// ---------- interaction ----------
function pick(ev) {
  if (!S) return;
  const r = view.getBoundingClientRect();
  const fx = Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width)), fy = Math.min(1, Math.max(0, (ev.clientY - r.top) / r.height));
  cross.hidden = false; cross.style.left = fx * 100 + "%"; cross.style.top = fy * 100 + "%"; $("hint").style.opacity = 0;
  const c = curve(Math.round(fx * (S.aw - 1)), Math.round(fy * (S.ah - 1))), best = argmax(c);
  const mx = Math.max(...c), mn = Math.min(...c), flat = mx < 1 || mx < 1.15 * mn;
  drawPlot(c, best); show(best);
  $("posNote").textContent = flat ? "Low-texture spot: sharpness barely changes, so the choice is unreliable." : `Sharpest at position ${best} for pixel (${Math.round(fx * S.w)}, ${Math.round(fy * S.h)}).`;
  $("info").textContent = `Peak/min sharpness ratio: ${(mx / Math.max(mn, 1e-6)).toFixed(1)}.`;
}
let dragging = false;
wrap.addEventListener("pointerdown", e => { dragging = true; wrap.setPointerCapture(e.pointerId); pick(e); });
wrap.addEventListener("pointermove", e => { if (dragging) pick(e); });
wrap.addEventListener("pointerup", () => { dragging = false; });
slider.addEventListener("input", () => { cross.hidden = true; show(+slider.value); $("posNote").textContent = "Frame chosen manually with the slider."; $("info").textContent = ""; });
window.addEventListener("keydown", e => {
  if (e.target.tagName === "SELECT") return;
  if (e.key === "ArrowRight") show(cur + 1); else if (e.key === "ArrowLeft") show(cur - 1);
});
$("depthChk").addEventListener("change", e => wrap.classList.toggle("showDepth", e.target.checked));
$("sweepBtn").addEventListener("click", () => { cross.hidden = true; let k = 0; show(0); const t = setInterval(() => { k++; if (k > 8) return clearInterval(t); show(k); }, 330); });

// ---------- stack management ----------
async function setStack(imgs, meta) {
  S = Object.assign(analyse(imgs), { imgs, ...meta });
  view.width = S.w; view.height = S.h; wrap.style.aspectRatio = `${S.w} / ${S.h}`;
  buildDepth();
  strip.innerHTML = "";
  imgs.forEach((im, i) => { const b = document.createElement("button"); b.type = "button"; b.title = "Position " + i;
    b.innerHTML = `<img src="${im.src}" alt="frame ${i}"><span>${i}</span>`; b.onclick = () => { cross.hidden = true; show(i); }; strip.appendChild(b); });
  $("about").textContent = `${meta.title}. ${meta.note || ""} (${S.w}×${S.h}px)`;
  cross.hidden = true; $("hint").style.opacity = 1; $("posNote").textContent = "No point selected yet."; $("info").textContent = "";
  pctx.clearRect(0, 0, plot.width, plot.height); cur = 0; anim = null; show(0);
}
async function loadStack(i) {
  const st = stacks[i];
  try { await setStack(await Promise.all(st.frames.map(loadImg)), st); }
  catch (e) { $("about").textContent = "Could not load this stack: " + e.message; }
}
$("stackSel").addEventListener("change", e => loadStack(+e.target.value));
$("upload").addEventListener("change", async e => {
  const files = [...e.target.files].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  if (files.length !== 9) { alert(`Please select exactly 9 frames (you chose ${files.length}). They are used in file-name order, near to far.`); return; }
  const imgs = await Promise.all(files.map(f => loadImg(URL.createObjectURL(f))));
  if (imgs.some(im => im.naturalWidth !== imgs[0].naturalWidth || im.naturalHeight !== imgs[0].naturalHeight)) { alert("All 9 frames must have the same size."); return; }
  await setStack(imgs, { title: "Your upload", note: "Frames used in file-name order (position 0 = first)." });
});

(async function init() {
  try {
    stacks = await (await fetch("stacks/index.json")).json();
    $("stackSel").innerHTML = stacks.map((s, i) => `<option value="${i}">${s.title}</option>`).join("");
    await loadStack(0);
  } catch (e) { $("about").textContent = "Could not load stacks/index.json (serve this folder over http, e.g. python -m http.server): " + e.message; }
})();

// ---- photo -> stack (GPU server behind the dashboard)
const genFile = $("genFile"), genBtn = $("genBtn"), genStatus = $("genStatus");
let genPhoto = null;
async function backendOnline() {
  try { const r = await (await fetch("api/backend")).json(); return !!r.online; } catch (e) { return false; }
}
async function refreshBackend() {
  const on = await backendOnline();
  genBtn.disabled = !on || !genPhoto;
  if (!genBtn.dataset.busy) genStatus.textContent = on ? (genPhoto ? "Ready." : "GPU server online. Choose a photo.") : "The GPU server is offline right now (it is only switched on while testing).";
}
async function shrink(file) {
  const bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
  const sc = Math.min(1, 1600 / Math.max(bmp.width, bmp.height)), c = document.createElement("canvas");
  c.width = Math.round(bmp.width * sc); c.height = Math.round(bmp.height * sc); c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
  return await new Promise(r => c.toBlob(r, "image/jpeg", 0.93));
}
genFile.addEventListener("change", async e => { genPhoto = e.target.files[0] || null; refreshBackend(); });
genBtn.addEventListener("click", async () => {
  if (!genPhoto) return;
  genBtn.disabled = true; genBtn.dataset.busy = 1; genStatus.textContent = "Uploading photo\u2026";
  try {
    const blob = await shrink(genPhoto);
    const r = await fetch("api/gen?pos=" + $("genPos").value, { method: "POST", body: blob });
    const j = await r.json(); if (!r.ok) throw new Error(j.error || r.status);
    for (;;) {
      await new Promise(r => setTimeout(r, 3000));
      const s = await (await fetch("api/gen/" + j.id)).json();
      if (s.state === "error") throw new Error(s.error);
      if (s.state === "done") {
        const frames = [0,1,2,3,4,5,6,7,8].map(i => `gen/${j.id}/frame_${i}.jpg`);
        const imgs = await Promise.all(frames.map(loadImg));
        const st = { name: "gen_" + j.id, title: "Your photo (generated)", source: "model", frames, note: `Generated from your photo (input at position ${$("genPos").value}) in ${s.seconds}s. The model invents the other focus positions; only the near-to-far order is reliable.` };
        stacks.push(st); const o = document.createElement("option"); o.value = stacks.length - 1; o.textContent = st.title + " " + j.id.slice(0, 4); $("stackSel").appendChild(o); $("stackSel").value = o.value;
        await setStack(imgs, st); genStatus.textContent = `Done in ${s.seconds}s - tap the image to refocus.`; break;
      }
      genStatus.textContent = (s.state === "queued" ? "Waiting for the GPU\u2026 " : "Generating\u2026 ") + Math.round(s.elapsed) + "s";
    }
  } catch (e) { genStatus.textContent = "Failed: " + e.message; }
  delete genBtn.dataset.busy; refreshBackend();
});
refreshBackend(); setInterval(refreshBackend, 15000);
