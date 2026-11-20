// Slide 3: the demo, and nothing else. Left: the recording of our viewer. Right: the three
// steps it shows, with before/after close-ups, so the slide also reads when the GIF is not
// playing (a PDF). Everything here comes from slides/demo/, written by scripts/build_demo.py.
const fs = require("fs");
const path = require("path");
const { asset, C, FONT, footer, title } = require("./theme");

const DEMO_DIR = asset("slides", "demo");
const DEMO_GIF = asset("slides", "demo.gif");
const GIF_BOX = Object.freeze({ x: 0.45, y: 1.2, w: 3.2, h: 3.95 }); // the GIF is fitted inside this
const COL = Object.freeze({ x: 3.95, w: 5.6 });
const RATIO = 7 / 5; // frame height / width (640 x 896 photos)

function loadDemo() {
  const file = path.join(DEMO_DIR, "demo.json");
  if (!fs.existsSync(file) || !fs.existsSync(DEMO_GIF)) throw new Error("Demo assets missing: run scripts/build_demo.py first");
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

/** Width and height of a GIF, read from its header (bytes 6-9, little-endian). */
function gifSize(file) {
  const head = fs.readFileSync(file).subarray(0, 10);
  if (head.toString("latin1", 0, 3) !== "GIF") throw new Error(file + " is not a GIF");
  return { width: head.readUInt16LE(6), height: head.readUInt16LE(8) };
}

/** Numbered step heading: amber disc with the number, then the step in bold. */
function stepHead(pres, s, n, text, y) {
  s.addText(String(n), {
    shape: pres.shapes.OVAL, x: COL.x, y, w: 0.26, h: 0.26, fill: { color: C.AMBER }, line: { color: C.AMBER, width: 0 },
    fontFace: FONT.BODY, fontSize: 11, bold: true, color: C.INK, align: "center", valign: "middle", margin: 0, objectName: "Step " + n,
  });
  s.addText(text, {
    x: COL.x + 0.36, y: y - 0.02, w: COL.w - 0.36, h: 0.3, fontFace: FONT.BODY, fontSize: 12.5, bold: true, color: C.WHITE, margin: 0, valign: "middle", isTextBox: true,
  });
}

function caption(s, text, x, y, w, color = C.SOFT) {
  s.addText(text, { x, y, w, h: 0.17, fontFace: FONT.BODY, fontSize: 7.5, color, align: "center", margin: 0, isTextBox: true });
}

function build(pres) {
  const demo = loadDemo();
  const s = pres.addSlide();
  s.background = { color: C.INK };
  title(s, "Demo: one photo in, click anywhere to refocus", { h: 0.45, fontSize: 22 });
  s.addText("Recorded from our click-to-refocus viewer. All 9 frames were generated from a single photo by " + demo.model + ".", {
    x: 0.45, y: 0.72, w: 9.1, h: 0.36, fontFace: FONT.BODY, fontSize: 10.5, color: C.SOFT, margin: 0, valign: "top", isTextBox: true, objectName: "Subtitle",
  });

  // The recording (animated in PowerPoint / Keynote / Google Slides; first frame in a PDF)
  const gif = gifSize(DEMO_GIF);
  const scale = Math.min(GIF_BOX.w / gif.width, GIF_BOX.h / gif.height);
  const gw = gif.width * scale, gh = gif.height * scale;
  s.addImage({ path: DEMO_GIF, x: GIF_BOX.x + (GIF_BOX.w - gw) / 2, y: GIF_BOX.y, w: gw, h: gh, objectName: "Demo GIF" });

  // Step 1: the input
  stepHead(pres, s, 1, "One input photo", 1.2);
  s.addText("This is all the model sees: one photo, taken at focus position " + demo.input_pos
    + " on a scale from 0 (nearest) to 8 (farthest). Nothing tells it how far away anything is.", {
    x: COL.x + 0.36, y: 1.5, w: COL.w - 0.36, h: 0.4, fontFace: FONT.BODY, fontSize: 10, color: C.SOFT, margin: 0, valign: "top", isTextBox: true,
  });

  // Step 2: the generated stack
  stepHead(pres, s, 2, "The model generates all 9 focus positions (a focal stack)", 2.04);
  const fw = 0.5, pitch = COL.w / 9, stripY = 2.38;
  Array.from({ length: 9 }, (_, i) => i).forEach((i) => {
    const x = COL.x + i * pitch;
    const isInput = i === demo.input_pos;
    s.addImage({ path: path.join(DEMO_DIR, "frame_" + i + ".jpg"), x, y: stripY, w: fw, h: fw * RATIO, objectName: "Frame " + i });
    if (isInput) s.addShape(pres.shapes.RECTANGLE, { x, y: stripY, w: fw, h: fw * RATIO, fill: { type: "none" }, line: { color: C.AMBER, width: 2 } });
    const tag = i === 0 ? "0 near" : i === 8 ? "8 far" : isInput ? i + " input" : String(i);
    caption(s, tag, x - 0.05, stripY + fw * RATIO + 0.02, fw + 0.1, isInput ? C.AMBER : C.SOFT);
  });

  // Step 3: the clicks, each as a close-up before and after
  stepHead(pres, s, 3, "Click a pixel: the viewer shows the frame that is sharpest there", 3.42);
  const side = 1.0, gap = 0.08, groupW = COL.w / demo.clicks.length, shotY = 4.1;
  demo.clicks.forEach((click, i) => {
    const x = COL.x + i * groupW;
    s.addText("Click on " + click.label, {
      x, y: 3.74, w: groupW - 0.2, h: 0.2, fontFace: FONT.BODY, fontSize: 10, bold: true, color: C.WHITE, margin: 0, valign: "middle", isTextBox: true,
    });
    caption(s, "before: input, frame " + demo.input_pos, x, shotY - 0.17, side);
    caption(s, "after the click: frame " + click.frame, x + side + gap, shotY - 0.17, side, C.AMBER);
    s.addImage({ path: path.join(DEMO_DIR, click.before), x, y: shotY, w: side, h: side, objectName: "Before " + (i + 1) });
    s.addImage({ path: path.join(DEMO_DIR, click.after), x: x + side + gap, y: shotY, w: side, h: side, objectName: "After " + (i + 1) });
    s.addShape(pres.shapes.RECTANGLE, { x: x + side + gap, y: shotY, w: side, h: side, fill: { type: "none" }, line: { color: C.AMBER, width: 1.5 } });
  });

  footer(s, true);
  return s;
}

module.exports = { build };
