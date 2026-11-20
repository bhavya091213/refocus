// Builds slides/44_Bhavya_Patel.pptx (the submission file name) and slides/speaker_notes.md.
// Usage: node build.js                      full deck
//        node build.js --only 2 --out x.pptx   one slide (for layout previews)
const fs = require("fs");
const path = require("path");
const util = require("util");
const pptxgen = require("pptxgenjs");
const JSZip = require("jszip");
const { C } = require("./theme");
const { NOTES, toMarkdown } = require("./notes");

const SLIDES = [require("./slide1"), require("./slide2"), require("./slide3")];
const DEFAULT_OUT = path.join(__dirname, "44_Bhavya_Patel.pptx");

function parseArgs(argv) {
  // strict: unknown flags and flags without a value throw instead of being ignored
  const { values } = util.parseArgs({ args: argv, options: { only: { type: "string" }, out: { type: "string" } }, strict: true });
  const only = values.only === undefined ? null : Number(values.only);
  if (only !== null && !(Number.isInteger(only) && only >= 1 && only <= SLIDES.length)) {
    throw new Error("--only must be a slide number from 1 to " + SLIDES.length);
  }
  if (only !== null && !values.out) throw new Error("--only needs --out, so a one-slide preview never replaces the full deck");
  return { only, out: path.resolve(values.out || DEFAULT_OUT) };
}

/** The library cannot colour bullets, so set the colour in the slide XML: every viewer then draws them the same. */
async function colourBullets(buffer, hex) {
  const zip = await JSZip.loadAsync(buffer);
  const names = Object.keys(zip.files).filter((n) => /^ppt\/slides\/slide\d+\.xml$/.test(n));
  await Promise.all(names.map(async (name) => {
    const xml = await zip.file(name).async("string");
    zip.file(name, xml.replace(/<a:buSzPct /g, '<a:buClr><a:srgbClr val="' + hex + '"/></a:buClr><a:buSzPct '));
  }));
  return zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}

async function main() {
  if (SLIDES.length !== NOTES.length) throw new Error("notes.js must have one entry per slide");
  const { only, out } = parseArgs(process.argv.slice(2));
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title = "Learning to Refocus a Single Photo";
  pres.author = "Bhavya";
  SLIDES.forEach((slide, i) => {
    if (only === null || only === i + 1) slide.build(pres).addNotes(NOTES[i]);
  });
  const raw = await pres.write({ outputType: "nodebuffer" });
  fs.writeFileSync(out, await colourBullets(raw, C.AMBER));
  if (only === null) fs.writeFileSync(path.join(__dirname, "speaker_notes.md"), toMarkdown(NOTES));
  process.stdout.write("written " + out + "\n");
}

main().catch((err) => {
  process.stderr.write("build failed: " + (err instanceof Error ? err.stack : String(err)) + "\n");
  process.exitCode = 1;
});
