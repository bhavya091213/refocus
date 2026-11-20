// Slide 1: the problem, how we trained, and the Blender test scenes.
// Text boxes are sized with about one spare line each, so a viewer whose font runs
// slightly wider still fits.
const { asset, C, FONT, footer, title, label, bullets } = require("./theme");

const PROBLEM = [
  "A lens is sharp at one distance; the rest is blurred, and blur destroys detail.",
  "Refocusing from one photo is ill-posed (no single right answer): many sharp scenes give the same blurry image, so the model must generate plausible detail, not average it.",
  "Task: 1 photo at a known focus position → all 9 positions (a focal stack) → click a pixel, show the frame sharpest there.",
];
const TRAINING = [
  "Data: 1,474 training and 164 test focal stacks from the original paper (phone photos, 9 frames each, 640×896 pixels).",
  "Start from pretrained Stable Video Diffusion and update only its temporal transformer blocks: 397.6 of the 1,524.6 million weights in the denoising network (U-Net).",
  "Each step: pick a random input frame, add noise to the 9 encoded frames, and minimise the mean squared denoising error (AdamW optimiser, learning rate 2×10⁻⁵).",
  "4,000 steps for each of 3 conditioning variants, in parallel on eight NVIDIA A100 graphics cards (GPUs): 3.4 hours, about $54.",
];
const BLENDER = [
  "We rendered scenes with true lens blur in Blender as real 9-frame stacks, so the right answer is known.",
  "From one frame, the authors’ released model gives a plausible near → far sweep, but its sharpest frame is 1–3 positions off.",
];

function card(pres, slide, x, y, w, h, name) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.07, fill: { color: C.INK2 }, line: { color: C.EDGE, width: 1 }, objectName: name,
  });
}

function build(pres) {
  const s = pres.addSlide();
  s.background = { color: C.INK };
  title(s, "A photo’s focus is fixed when you take it. We want to move it afterwards.", { h: 0.85 });

  // Left: the problem
  label(s, "THE PROBLEM", 0.45, 1.25, 4.3);
  bullets(s, PROBLEM, { x: 0.45, y: 1.52, w: 4.3, h: 2.0 }, { fontSize: 11.5, paraSpaceAfter: 6 });
  const frames = [["f0", "position 0 (near)"], ["f4", "position 4"], ["f8", "position 8 (far)"]];
  frames.forEach(([file, cap], i) => {
    const x = 0.45 + i * 1.0;
    s.addImage({ path: asset("remotion", "public", "frames", file + ".jpg"), x, y: 3.66, w: 0.82, h: 1.148, objectName: "Frame " + file });
    s.addText(cap, { x: x - 0.09, y: 4.84, w: 1.0, h: 0.2, fontFace: FONT.BODY, fontSize: 8, color: C.SOFT, align: "center", margin: 0, isTextBox: true });
  });
  s.addText("One real scene at 3 of its 9 focus positions. A normal photo keeps only one of them.", {
    x: 3.42, y: 3.66, w: 1.33, h: 1.15, fontFace: FONT.BODY, fontSize: 9.5, italic: true, color: C.SOFT, margin: 0, valign: "middle", isTextBox: true,
  });

  // Right, top: how we trained
  card(pres, s, 5.0, 1.22, 4.55, 2.28, "Training card");
  label(s, "HOW WE TRAINED", 5.14, 1.31, 4.2);
  bullets(s, TRAINING, { x: 5.24, y: 1.58, w: 4.2, h: 1.88 }, { fontSize: 10, paraSpaceAfter: 3 });

  // Right, bottom: Blender
  card(pres, s, 5.0, 3.6, 4.55, 1.54, "Blender card");
  label(s, "TESTING IN BLENDER", 5.14, 3.68, 4.2);
  const renders = [["frame_4.jpg", "focus on duck"], ["frame_7.jpg", "focus on cat"]];
  renders.forEach(([file, cap], i) => {
    const x = 5.14 + i * 0.76;
    s.addImage({ path: asset("viewer", "stacks", "blender_macro", file), x, y: 3.95, w: 0.7, h: 0.98, objectName: "Blender " + file });
    s.addText(cap, { x: x - 0.03, y: 4.94, w: 0.76, h: 0.17, fontFace: FONT.BODY, fontSize: 7.5, color: C.SOFT, align: "center", margin: 0, isTextBox: true });
  });
  bullets(s, BLENDER, { x: 6.82, y: 3.93, w: 2.64, h: 1.18 }, { fontSize: 9.5, paraSpaceAfter: 3, indent: 9 });

  footer(s, true);
  return s;
}

module.exports = { build };
