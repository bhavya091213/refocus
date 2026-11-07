const pptxgen = require("pptxgenjs");
const R = "D:/Refocus/";
const INK = "0E1A2B", INK2 = "1B2B42", AMBER = "F2A33A", PAPER = "F6F7F9", TEXT = "1B2433", MUTED = "5B6678", WHITE = "FFFFFF", SOFT = "B9C4D6";
const HEAD = "Cambria", BODY = "Calibri";
const CITE = "Based on Tedla, Zhang, Zhang & Xin, \u201CLearning to Refocus with Video Diffusion Models,\u201D SIGGRAPH Asia 2025 \u00B7 learn2refocus.github.io";

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "Learning to Refocus a Single Photo";
pres.author = "Bhavya";

function footer(s, dark) {
  s.addText(CITE, { x: 0.5, y: 5.15, w: 9, h: 0.3, fontFace: BODY, fontSize: 10, color: dark ? SOFT : MUTED, margin: 0, isTextBox: true, objectName: "Credit" });
}

// ---------- Slide 1 ----------
{
  const s = pres.addSlide(); s.background = { color: INK };
  s.addText("One photo in, a full focal stack out", { x: 0.5, y: 0.4, w: 5.0, h: 1.35, fontFace: HEAD, fontSize: 34, bold: true, color: WHITE, margin: 0, valign: "top", isTextBox: true, objectName: "Title" });
  s.addText([
    { text: "Goal: ", options: { bold: true, color: AMBER } }, { text: "click any pixel and bring it into focus", options: { breakLine: true } },
    { text: "Idea: ", options: { bold: true, color: AMBER } }, { text: "a focal sweep is a 9-frame \u201Cvideo\u201D, so fine-tune a video diffusion model (Stable Video Diffusion)", options: { breakLine: true } },
    { text: "Trained: ", options: { bold: true, color: AMBER } }, { text: "only the temporal blocks; image encoder and decoder stay frozen" },
  ], { x: 0.5, y: 1.85, w: 4.9, h: 1.85, fontFace: BODY, fontSize: 15, color: WHITE, paraSpaceAfter: 8, margin: 0, valign: "top", isTextBox: true, objectName: "Bullets" });

  // real focal-stack frames from the dataset
  const fr = [["f0", "pos 0 \u00B7 near"], ["f4", "pos 4"], ["f8", "pos 8 \u00B7 far"]];
  fr.forEach((f, i) => {
    const x = 5.65 + i * 1.3;
    s.addImage({ path: R + "remotion/public/frames/" + f[0] + ".jpg", x, y: 0.45, w: 1.2, h: 1.68, objectName: "Frame " + f[0] });
    s.addText(f[1], { x, y: 2.17, w: 1.2, h: 0.25, fontFace: BODY, fontSize: 10, color: SOFT, align: "center", margin: 0, isTextBox: true });
  });
  s.addText("Three of the nine frames in one real training stack", { x: 5.65, y: 2.5, w: 3.8, h: 0.3, fontFace: BODY, fontSize: 11, italic: true, color: SOFT, margin: 0, isTextBox: true });

  const steps = [["1 photo", "any focus position"], ["Video diffusion", "temporal blocks tuned"], ["9-frame stack", "near \u2192 far"], ["Click a pixel", "show sharpest frame"]];
  steps.forEach((st, i) => {
    const x = 0.5 + i * 2.35;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.85, w: 2.0, h: 0.95, rectRadius: 0.08, fill: { color: i === 1 ? AMBER : INK2 }, line: { color: i === 1 ? AMBER : "2E4160", width: 1 }, objectName: "Step " + (i + 1) });
    s.addText([{ text: st[0], options: { bold: true, fontSize: 15, breakLine: true } }, { text: st[1], options: { fontSize: 11 } }],
      { x, y: 3.85, w: 2.0, h: 0.95, fontFace: BODY, color: i === 1 ? INK : WHITE, align: "center", valign: "middle", margin: 4, isTextBox: true });
    if (i < 3) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.04, y: 4.22, w: 0.26, h: 0.2, fill: { color: AMBER }, line: { color: AMBER, width: 0 }, objectName: "Arrow" });
  });
  footer(s, true);
  s.addNotes("SLIDE 1 (about 55 seconds). Phones and cameras bake the focus into a photo. Our project: give the model one image, and let you click anywhere to refocus it afterwards. We do that by generating a focal stack: nine frames from near to far, like a tiny video where only the focus plane moves. That is why we start from a video diffusion model, Stable Video Diffusion, as in the SIGGRAPH Asia 2025 paper by Tedla and colleagues, which we credit and reproduce. We keep the image encoder and decoder frozen and fine-tune only the temporal transformer blocks, the part that links frames to each other. The top right shows three real frames from one training stack: near, middle, far. The row at the bottom is the pipeline: one photo, the video model, nine frames, and then your click simply picks the frame that is sharpest at that pixel.");
}

// ---------- Slide 2 ----------
{
  const s = pres.addSlide(); s.background = { color: PAPER };
  s.addText("Slot conditioning beats motion-bucket encoding", { x: 0.5, y: 0.35, w: 9, h: 0.6, fontFace: HEAD, fontSize: 28, bold: true, color: INK, margin: 0, isTextBox: true, objectName: "Title" });
  s.addText("We fine-tuned three ways of telling the model the input\u2019s focus position, then tested on 20 held-out scenes \u00D7 3 input positions", { x: 0.5, y: 0.98, w: 9, h: 0.5, fontFace: BODY, fontSize: 14, color: MUTED, margin: 0, valign: "top", isTextBox: true });

  const H = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: INK }, align: "center", fontSize: 12 } });
  const L = (t, o = {}) => ({ text: t, options: Object.assign({ align: "left", fontSize: 12, color: TEXT }, o) });
  const N = (t, o = {}) => ({ text: t, options: Object.assign({ align: "center", fontSize: 12, color: TEXT }, o) });
  const rows = [
    [Object.assign(H("Model"), { options: { bold: true, color: WHITE, fill: { color: INK }, align: "left", fontSize: 12 } }), H("PSNR \u2191"), H("SSIM \u2191"), H("LPIPS \u2193"), H("Depth \u03C1")],
    [L("Authors\u2019 200k checkpoint", { bold: true }), N("31.07"), N("0.893"), N("0.160"), N("\u22120.70")],
    [L("A  random slot (ours)"), N("28.76"), N("0.870", { bold: true }), N("0.192", { bold: true }), N("\u22120.61")],
    [L("B  position ablated (ours)"), N("29.11", { bold: true }), N("0.863"), N("0.196"), N("\u22120.58")],
    [L("C  motion_bucket_id (ours)", { color: "A33A2A" }), N("28.62", { color: "A33A2A" }), N("0.858", { color: "A33A2A" }), N("0.199", { color: "A33A2A" }), N("\u22120.61", { color: "A33A2A" })],
  ];
  s.addTable(rows, { x: 0.5, y: 1.6, w: 5.7, colW: [2.3, 0.85, 0.85, 0.85, 0.85], rowH: 0.38, fontFace: BODY, border: { type: "solid", color: "D5DAE3", pt: 0.75 }, fill: { color: WHITE }, valign: "middle", objectName: "Results table" });
  s.addText("Bold = best of our three arms. Depth \u03C1: how well the sharpest frame follows scene depth (real stacks: \u22120.76; more negative is better).", { x: 0.5, y: 3.57, w: 5.7, h: 0.45, fontFace: BODY, fontSize: 10, color: MUTED, margin: 0, valign: "top", isTextBox: true });

  s.addText([
    { text: "B beats C on every metric (+0.49 dB, 55 of 60 items); A beats C on SSIM and LPIPS.", options: { breakLine: true, bullet: true } },
    { text: "A vs B is a trade-off: B has higher PSNR (+0.35 dB), A better SSIM and LPIPS.", options: { breakLine: true, bullet: true } },
    { text: "The authors\u2019 model leads everywhere; ours trained 2% as long.", options: { bullet: true } },
  ], { x: 0.5, y: 4.05, w: 5.7, h: 1.05, fontFace: BODY, fontSize: 13, color: TEXT, paraSpaceAfter: 3, margin: 0, valign: "top", isTextBox: true, objectName: "Takeaways" });

  const stats = [["8 \u00D7 A100", "3.4 h \u00B7 about $54"], ["4,000", "steps per arm (2% of the 200k)"], ["20 \u00D7 3", "scenes \u00D7 input positions"]];
  stats.forEach((st, i) => {
    const y = 1.6 + i * 1.2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.55, y, w: 2.95, h: 1.05, rectRadius: 0.08, fill: { color: INK }, line: { color: INK, width: 0 }, objectName: "Stat card " + (i + 1) });
    s.addText([{ text: st[0], options: { fontFace: HEAD, bold: true, fontSize: 26, color: AMBER, breakLine: true } }, { text: st[1], options: { fontFace: BODY, fontSize: 12, color: WHITE } }],
      { x: 6.55, y, w: 2.95, h: 1.05, align: "center", valign: "middle", margin: 4, isTextBox: true });
  });
  footer(s, false);
  s.addNotes("SLIDE 2 (about 65 seconds). We trained three versions of the model, which is our ablation. A tells the model the input's focus position by putting the input photo in the matching slot of the nine frames, as the authors do. B hides the position: the photo is copied into every slot. C passes the position as a single number through the motion-bucket input instead. We trained each for 4,000 steps on eight A100 GPUs, about 3.4 hours and about 54 dollars, which is only 2 percent of the authors' 200,000 steps. Then we tested on 20 held-out scenes at three input positions. The authors' checkpoint wins everywhere, as expected. Among ours, C is clearly weakest: on the same 60 items B beats it by about half a decibel, in 55 out of 60. A versus B is a trade-off: B has higher PSNR, A has better SSIM and LPIPS. Honest caveat: one seed, short training, 20 scenes.");
}

// ---------- Slide 3 ----------
{
  const s = pres.addSlide(); s.background = { color: INK };
  s.addText("Demo, a depth check, and the caveats", { x: 0.5, y: 0.35, w: 9, h: 0.6, fontFace: HEAD, fontSize: 28, bold: true, color: WHITE, margin: 0, isTextBox: true, objectName: "Title" });
  s.addImage({ path: R + "report/compare_macro_in4.jpg", x: 0.5, y: 1.15, w: 4.9, h: 2.376, objectName: "Blender comparison" });
  s.addText("Blender scene: true focal stack (top) vs. model output from one photo", { x: 0.5, y: 3.57, w: 4.9, h: 0.3, fontFace: BODY, fontSize: 10, italic: true, color: SOFT, margin: 0, isTextBox: true });
  s.addImage({ path: R + "report/depth_vs_focus.png", x: 5.7, y: 1.15, w: 3.8, h: 1.382, objectName: "Depth vs focus" });
  s.addText("Extra credit: the sharpest frame tracks monocular depth (Depth Anything V2), Spearman \u03C1 = \u22120.80 on 16 scenes", { x: 5.7, y: 2.6, w: 3.8, h: 0.6, fontFace: BODY, fontSize: 11, italic: true, color: SOFT, margin: 0, valign: "top", isTextBox: true });

  const cards = [
    ["Click-to-refocus viewer", "Click a pixel; the page shows the nearest of the 9 frames."],
    ["Synthetic test", "Blender scenes with a real sweep: plausible near-to-far order, peaks off by 1\u20133 positions."],
    ["Limits", "Short training, one seed, 20 scenes; Blender distances are our assumption."],
  ];
  cards.forEach((c, i) => {
    const x = 0.5 + i * 3.1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.95, w: 2.9, h: 1.1, rectRadius: 0.08, fill: { color: INK2 }, line: { color: "2E4160", width: 1 }, objectName: "Card " + (i + 1) });
    s.addText([{ text: c[0], options: { bold: true, fontSize: 13, color: AMBER, breakLine: true } }, { text: c[1], options: { fontSize: 11, color: WHITE } }],
      { x: x + 0.08, y: 3.95, w: 2.74, h: 1.1, fontFace: BODY, valign: "middle", margin: 2, isTextBox: true });
  });
  s.addText(CITE, { x: 0.5, y: 5.2, w: 9, h: 0.28, fontFace: BODY, fontSize: 10, color: SOFT, margin: 0, isTextBox: true, objectName: "Credit" });
  s.addNotes("SLIDE 3 (about 60 seconds). For the demo we also built test scenes in Blender with free Poly Haven assets and real thin-lens blur, so we know the true focus stack. On the left, the top row is the ground truth and the middle row is what the model produced from one photo: it sweeps focus from near to far in a believable order, but its sharpest frames land one to three positions off, and we cannot yet tell whether that is our guess about the focus distances or the synthetic-to-real gap. For extra credit we checked a link to depth: the frame where each pixel is sharpest correlates with monocular depth, Spearman minus 0.80, which suggests depth could help future versions. The click-to-refocus viewer lets you click a pixel and shows the nearest frame. Limits: short training, one seed, 20 test scenes. This builds on Tedla and colleagues, SIGGRAPH Asia 2025, which we credit on every slide. Thank you.");
}

pres.writeFile({ fileName: "D:/Refocus/slides/refocus_slides.pptx" }).then(() => console.log("written"));
