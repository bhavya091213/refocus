// Shared look and small drawing helpers for the deck. One font everywhere, Arial: it ships with
// Windows and macOS, Google Slides has it, and LibreOffice swaps in a metric-identical face, so
// text takes the same space wherever the deck is opened. SLIDE_FONT overrides it for a layout
// stress test with a wider face (for example SLIDE_FONT=Verdana).
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const asset = (...parts) => path.join(ROOT, ...parts);

const C = Object.freeze({
  INK: "0E1A2B", INK2: "1B2B42", EDGE: "2E4160", AMBER: "F2A33A", PAPER: "F6F7F9",
  TEXT: "1B2433", MUTED: "5B6678", WHITE: "FFFFFF", SOFT: "B9C4D6", RULE: "D5DAE3",
  FROZEN: "DCE8F7", FROZEN_EDGE: "6F97C9", TRAINED: "FBD49A", TRAINED_EDGE: "D98A1F",
  PLAIN: "ECEFF4", PLAIN_EDGE: "AEB7C6", WARN: "A33A2A",
});
const FACE = process.env.SLIDE_FONT || "Arial";
const FONT = Object.freeze({ HEAD: FACE, BODY: FACE });

const CITE_SHORT =
  "Based on Tedla, Zhang, Zhang & Xin, “Learning to Refocus with Video Diffusion Models,” SIGGRAPH Asia 2025 · learn2refocus.github.io";

/** One-line credit at the bottom of a slide. */
function footer(slide, dark) {
  slide.addText(CITE_SHORT, {
    x: 0.45, y: 5.24, w: 9.1, h: 0.26, fontFace: FONT.BODY, fontSize: 9,
    color: dark ? C.SOFT : C.MUTED, margin: 0, isTextBox: true, objectName: "Credit",
  });
}

/** Slide title in the heading face. */
function title(slide, text, opts = {}) {
  slide.addText(text, {
    x: 0.45, y: 0.26, w: 9.1, h: 0.8, fontFace: FONT.HEAD, fontSize: 23, bold: true,
    color: C.WHITE, margin: 0, valign: "top", isTextBox: true, objectName: "Title", ...opts,
  });
}

/** Small amber section label, e.g. "THE PROBLEM". */
function label(slide, text, x, y, w, color = C.AMBER) {
  slide.addText(text, {
    x, y, w, h: 0.24, fontFace: FONT.BODY, fontSize: 10.5, bold: true, color,
    charSpacing: 1.5, margin: 0, isTextBox: true,
  });
}

/** Bulleted paragraphs; `items` are plain strings. */
function bullets(slide, items, box, style = {}) {
  const { indent = 11, ...textStyle } = style;
  const runs = items.map((text, i) => ({
    text, options: { bullet: { indent }, breakLine: i < items.length - 1 },
  }));
  slide.addText(runs, {
    fontFace: FONT.BODY, fontSize: 11, color: C.WHITE, paraSpaceAfter: 5, margin: 0,
    valign: "top", isTextBox: true, ...box, ...textStyle,
  });
}

/** Straight arrow from (x1, y1) to (x2, y2); must be horizontal or vertical. */
function arrow(pres, slide, x1, y1, x2, y2, color = C.TEXT) {
  slide.addShape(pres.shapes.LINE, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipH: x2 < x1, flipV: y2 < y1,
    line: { color, width: 1.5, endArrowType: "triangle" }, objectName: "Arrow",
  });
}

module.exports = { ROOT, asset, C, FONT, CITE_SHORT, footer, title, label, bullets, arrow };
