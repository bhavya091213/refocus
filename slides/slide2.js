// Slide 2: the architecture as a flowchart. Every parameter count is read from
// slides/arch_params.json, which scripts/count_params.py computes from the model
// configs; the totals match the counts taken from the real checkpoint (report, Section 4).
// Short forms used in the diagram are spelled out in the key at the bottom of the slide.
const { asset, C, FONT, title, bullets, arrow } = require("./theme");
const P = require("./arch_params.json");

const M = (n) => (n / 1e6).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " M";

const KIND = Object.freeze({
  frozen: { fill: C.FROZEN, edge: C.FROZEN_EDGE },
  trained: { fill: C.TRAINED, edge: C.TRAINED_EDGE },
  plain: { fill: C.PLAIN, edge: C.PLAIN_EDGE },
});

const ATTRIBUTION =
  "Method and architecture: Tedla, Zhang, Zhang & Xin, “Learning to Refocus with Video Diffusion Models,” SIGGRAPH Asia 2025 "
  + "(doi.org/10.1145/3757377.3763873), built on Stable Video Diffusion (Blattmann et al., 2023, arXiv:2311.15127).";
const ABBREVIATIONS =
  "Abbreviations: M = million parameters · VAE = variational autoencoder · CLIP = Contrastive Language–Image Pre-training · "
  + "ViT-H/14 = Vision Transformer, Huge size, 14-pixel patches · U-Net = U-shaped denoising network · "
  + "A100 = an NVIDIA graphics card (GPU) with 40 gigabytes (GB) of memory";

/** A flowchart node: optional bold name on the first line, detail lines under it. */
function node(pres, slide, kind, box, name, details, sizes = {}) {
  const k = KIND[kind];
  const { nameSize = 10, detailSize = 8.5 } = sizes;
  const head = name ? [{ text: name, options: { bold: true, fontSize: nameSize, breakLine: details.length > 0 } }] : [];
  const runs = head.concat(details.map((text, i) => ({ text, options: { fontSize: detailSize, breakLine: i < details.length - 1 } })));
  slide.addText(runs, {
    shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.05, ...box,
    fill: { color: k.fill }, line: { color: k.edge, width: 1.25 },
    fontFace: FONT.BODY, color: C.TEXT, align: "center", valign: "middle", margin: 3, objectName: name || details[0],
  });
}

function small(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, { x, y, w, h, fontFace: FONT.BODY, fontSize: 8, color: C.MUTED, margin: 0, align: "center", valign: "middle", isTextBox: true, ...opts });
}

/** Temporal transformer blocks grouped by channel width: [{ width, count, each }]. */
function temporalBlocksByWidth(unet) {
  const counts = Object.entries(unet.by_block).reduce((acc, [name, parts]) => {
    const attn = unet.attention_per_module[name];
    if (!attn || !parts.temporal_transformer) return acc;
    const each = unet.temporal_transformer_block_internals[String(attn.channels)].params;
    return { ...acc, [attn.channels]: (acc[attn.channels] || 0) + Math.round(parts.temporal_transformer / each) };
  }, {});
  return Object.keys(counts).map(Number).sort((a, b) => a - b).map((width) => ({
    width, count: counts[width], each: unet.temporal_transformer_block_internals[String(width)].params,
  }));
}

function legend(pres, slide, frozenTotal, trainedTotal) {
  const items = [
    [KIND.frozen, "pretrained, kept frozen: " + M(frozenTotal), 2.85],
    [KIND.trained, "pretrained, then fine-tuned by us: " + M(trainedTotal), 3.3],
    [KIND.plain, "no weights", 1.1],
  ];
  items.reduce((x, [k, text, w]) => {
    slide.addShape(pres.shapes.RECTANGLE, { x, y: 1.07, w: 0.16, h: 0.14, fill: { color: k.fill }, line: { color: k.edge, width: 1 } });
    slide.addText(text, { x: x + 0.22, y: 1.03, w: w - 0.25, h: 0.22, fontFace: FONT.BODY, fontSize: 9, color: C.TEXT, margin: 0, valign: "middle", isTextBox: true });
    return x + w;
  }, 0.4);
}

function unetNode(pres, slide, x, y, w, h) {
  const u = P.unet, cat = u.overall_by_category, trained = u.trainable_temporal_transformer;
  const maps = u.feature_maps;
  const inner = { nameSize: 9.5, detailSize: 8 };
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.05, fill: { color: C.WHITE }, line: { color: C.TEXT, width: 1.25 }, objectName: "U-Net" });
  slide.addText([
    { text: "U-Net denoiser", options: { bold: true, fontSize: 11, breakLine: true } },
    { text: M(u.total) + " · run for 25 denoising steps", options: { fontSize: 8.5 } },
  ], { x, y: y + 0.03, w, h: 0.36, fontFace: FONT.BODY, color: C.TEXT, align: "center", valign: "middle", margin: 0, isTextBox: true });
  node(pres, slide, "frozen", { x: x + 0.1, y: y + 0.4, w: w - 0.2, h: 0.7 }, "All other layers: frozen, " + M(u.total - trained), [
    "spatial residual blocks " + M(cat.spatial_resnet),
    "temporal residual blocks " + M(cat.temporal_resnet),
    "spatial attention " + M(cat.spatial_transformer) + ", other " + M(cat.other + cat.sampler_conv),
  ], inner);
  const perWidth = temporalBlocksByWidth(u);
  node(pres, slide, "trained", { x: x + 0.1, y: y + 1.14, w: w - 0.2, h: 0.56 }, u.num_temporal_transformer_blocks + " temporal transformer blocks", [
    "TRAINED BY US: " + M(trained) + " (" + Math.round(u.trainable_pct) + "%)",
    perWidth.map((b) => b.count + " × " + M(b.each)).join(" + "),
  ], inner);
  const sizes = ["down_block_0", "down_block_1", "down_block_2", "down_block_3"]
    .map((b) => maps[b].h_during_block + "×" + maps[b].w_during_block);
  slide.addText([
    { text: "channel widths " + u.block_out_channels.join(" / "), options: { breakLine: true } },
    { text: "feature maps " + sizes.join(" → ") },
  ], { x, y: y + 1.72, w, h: 0.28, fontFace: FONT.BODY, fontSize: 7.5, color: C.MUTED, margin: 0, align: "center", valign: "middle", isTextBox: true });
}

const CARDS = [
  ["What the block we trained does", [
    "A temporal transformer is attention along the frame axis: each location looks at itself in the other 8 frames.",
    "It decides how frames relate, so we re-teach it that the axis is focus distance, not motion.",
    "Layers: normalise → feed-forward → self-attention over frames → cross-attention to the CLIP token → feed-forward.",
  ]],
  ["Why we chose this", [
    "Freeze the VAE, CLIP and the spatial layers: they already know how sharp and blurred images look.",
    "Train only the temporal blocks: 1,474 stacks cannot support retraining 2.25 billion weights, and this fits one 40 GB A100 graphics card.",
    "Slot conditioning adds no weights: the slot the input sits in encodes its focus position.",
  ]],
  ["Why video was the easiest route", [
    "A focal stack already is a video: the scene stays put while one thing changes smoothly across frames.",
    "Stable Video Diffusion comes pretrained with both things we need: realistic images and consistent frames.",
    "Nothing to redesign: 9 focus positions go where video frames went. Training from scratch was far beyond our $100.",
  ]],
];

function build(pres) {
  const s = pres.addSlide();
  s.background = { color: C.PAPER };
  const total = P.unet.total + P.vae.total + P.clip.total;
  const trained = P.unet.trainable_temporal_transformer;

  title(s, "Architecture: what is pretrained, what we trained", { y: 0.2, h: 0.42, fontSize: 21, color: C.INK });
  s.addText([
    { text: ATTRIBUTION, options: { bold: true } },
    { text: " Parameter counts are our own measurements." },
  ], { x: 0.4, y: 0.63, w: 9.2, h: 0.36, fontFace: FONT.BODY, fontSize: 8.8, color: C.MUTED, margin: 0, valign: "top", isTextBox: true, objectName: "Attribution" });
  legend(pres, s, total - trained, trained);

  // ---- flowchart: two rows, the U-Net spans both ----
  const top = 1.3, rowH = 0.86, bot = 2.46, span = bot + rowH - top;
  const mid = (y) => y + rowH / 2;
  const X = Object.freeze({ input: 0.4, enc: 1.58, slot: 3.26, unet: 4.99, dec: 7.9 });
  const W = Object.freeze({ input: 0.95, enc: 1.45, slot: 1.5, unet: 2.68, dec: 1.7 });
  const NOISE = Object.freeze({ y: 2.2, h: 0.4 });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X.input, y: top, w: W.input, h: span, rectRadius: 0.05, fill: { color: C.PLAIN }, line: { color: C.PLAIN_EDGE, width: 1.25 }, objectName: "Input" });
  s.addImage({ path: asset("remotion", "public", "frames", "f4.jpg"), x: X.input + 0.1, y: top + 0.1, w: 0.75, h: 1.05 });
  s.addText([
    { text: "1 photo", options: { bold: true, fontSize: 10, breakLine: true } },
    { text: "640×896 pixels,", options: { fontSize: 8.5, breakLine: true } },
    { text: "focus position k", options: { fontSize: 8.5, breakLine: true } },
    { text: "(0 near to 8 far)", options: { fontSize: 8.5 } },
  ], { x: X.input, y: top + 1.2, w: W.input, h: span - 1.25, fontFace: FONT.BODY, color: C.TEXT, align: "center", valign: "middle", margin: 0, isTextBox: true });

  node(pres, s, "frozen", { x: X.enc, y: top, w: W.enc, h: rowH }, "VAE encoder", ["frozen · " + M(P.vae.encoder), "3×896×640 → 4×112×80", "(1/" + P.vae.spatial_downsample_factor + " of the size)"]);
  node(pres, s, "frozen", { x: X.enc, y: bot, w: W.enc, h: rowH }, "CLIP ViT-H/" + P.clip.patch_size, ["frozen · " + M(P.clip.total), P.clip.layers + " layers, width " + P.clip.hidden_size, "1 token of " + P.clip.projection_dim + " numbers"]);
  node(pres, s, "plain", { x: X.slot, y: top, w: W.slot, h: rowH }, "Slot conditioning", ["no weights", "latent goes in slot k of 9,", "the other 8 are zeros"]);
  node(pres, s, "plain", { x: X.slot, y: NOISE.y, w: W.slot, h: NOISE.h }, null, ["+ 9 noisy latents", "= 8 channels into U-Net"], { detailSize: 8 });
  unetNode(pres, s, X.unet, top, W.unet, span);
  node(pres, s, "frozen", { x: X.dec, y: top, w: W.dec, h: rowH }, "VAE temporal decoder", ["frozen · " + M(P.vae.decoder), "4×112×80 → 3×896×640", "for each of 9 frames"]);

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X.dec, y: bot, w: W.dec, h: rowH, rectRadius: 0.05, fill: { color: C.PLAIN }, line: { color: C.PLAIN_EDGE, width: 1.25 }, objectName: "Output" });
  s.addText("9-frame focal stack", { x: X.dec, y: bot + 0.05, w: W.dec, h: 0.2, fontFace: FONT.BODY, fontSize: 10, bold: true, color: C.TEXT, align: "center", margin: 0, isTextBox: true });
  Array.from({ length: 9 }, (_, i) => i).forEach((i) => {
    s.addImage({ path: asset("remotion", "public", "frames", "f" + i + ".jpg"), x: X.dec + 0.055 + i * 0.178, y: bot + 0.29, w: 0.168, h: 0.235 });
  });
  small(s, "near → far; a click shows the frame sharpest at that pixel", X.dec + 0.05, bot + 0.55, W.dec - 0.1, 0.28, { fontSize: 7.5, color: C.TEXT });

  const right = (k) => X[k] + W[k];
  const noiseMid = NOISE.y + NOISE.h / 2;
  arrow(pres, s, right("input"), mid(top), X.enc, mid(top));
  arrow(pres, s, right("input"), mid(bot), X.enc, mid(bot));
  arrow(pres, s, right("enc"), mid(top), X.slot, mid(top));
  arrow(pres, s, right("slot"), mid(top), X.unet, mid(top));
  arrow(pres, s, right("slot"), noiseMid, X.unet, noiseMid);
  arrow(pres, s, right("enc"), mid(bot), X.unet, mid(bot));
  arrow(pres, s, right("unet"), mid(top), X.dec, mid(top));
  arrow(pres, s, X.dec + W.dec / 2, top + rowH, X.dec + W.dec / 2, bot);
  small(s, "one token → cross-attention", right("enc") + 0.05, mid(bot) - 0.21, X.unet - right("enc") - 0.1, 0.18);

  // ---- three explanation cards ----
  const cardY = 3.42, cardH = 1.66;
  CARDS.forEach(([head, items], i) => {
    const x = 0.4 + i * 3.11;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cardY, w: 2.98, h: cardH, rectRadius: 0.05, fill: { color: C.WHITE }, line: { color: i === 0 ? C.TRAINED_EDGE : C.RULE, width: i === 0 ? 1.5 : 1 }, objectName: head });
    s.addText(head, { x: x + 0.1, y: cardY + 0.05, w: 2.78, h: 0.24, fontFace: FONT.BODY, fontSize: 10.5, bold: true, color: C.INK, margin: 0, valign: "middle", isTextBox: true });
    bullets(s, items, { x: x + 0.17, y: cardY + 0.31, w: 2.73, h: cardH - 0.34 }, { fontSize: 8.5, color: C.TEXT, paraSpaceAfter: 2, indent: 8 });
  });

  s.addText(ABBREVIATIONS, {
    x: 0.4, y: 5.13, w: 9.2, h: 0.3, fontFace: FONT.BODY, fontSize: 7.5, color: C.MUTED, margin: 0, valign: "top", isTextBox: true, objectName: "Abbreviations",
  });
  return s;
}

module.exports = { build };
