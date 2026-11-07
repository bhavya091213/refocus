import io
V = "D:/Refocus/viewer/"
h = io.open(V + "index.html", encoding="utf-8", newline="").read()
assert "genCard" not in h
card = '''    <div class="card" id="genCard">
      <h2>Make a stack from your own photo</h2>
      <p class="muted small">Pick or take one photo. A cloud GPU runs the diffusion model and returns 9 focus positions (about 1&ndash;3 minutes). <b>Your photo is sent to that server.</b></p>
      <div class="controls" style="margin-top:8px">
        <label class="upload">Choose / take photo<input type="file" id="genFile" accept="image/*"></label>
        <label>Photo is focused on
          <select id="genPos"><option value="1">something very close</option><option value="4" selected>something at mid distance</option><option value="7">something far away</option></select>
        </label>
        <button id="genBtn" type="button" disabled>Generate focal stack</button>
      </div>
      <p id="genStatus" class="muted small">Checking GPU server&hellip;</p>
    </div>
'''
h = h.replace('<div class="canvasWrap" id="wrap">', card + '\n    <div class="canvasWrap" id="wrap">', 1)
h = h.replace("nothing is uploaded anywhere.", "stored stacks and uploads of 9 frames stay on your device; the optional photo generator sends your photo to a cloud GPU server.")
io.open(V + "index.html", "w", encoding="utf-8", newline="").write(h)

a = io.open(V + "app.js", encoding="utf-8", newline="").read()
js = '''
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
  genBtn.disabled = true; genBtn.dataset.busy = 1; genStatus.textContent = "Uploading photo\\u2026";
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
      genStatus.textContent = (s.state === "queued" ? "Waiting for the GPU\\u2026 " : "Generating\\u2026 ") + Math.round(s.elapsed) + "s";
    }
  } catch (e) { genStatus.textContent = "Failed: " + e.message; }
  delete genBtn.dataset.busy; refreshBackend();
});
refreshBackend(); setInterval(refreshBackend, 15000);
'''
a = a.rstrip() + "\n" + js
io.open(V + "app.js", "w", encoding="utf-8", newline="").write(a); print("ok")
