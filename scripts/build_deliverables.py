"""Copy final deliverables into dashboard/public and write public/deliverables.json (shown on the Deliverables tab)."""
import json, os, shutil, glob
R = "D:/Refocus/"; P = R + "dashboard/public/"
os.makedirs(P + "remotion", exist_ok=True)
def cp(src, dst):
    if os.path.exists(src):
        os.makedirs(os.path.dirname(P + dst), exist_ok=True); shutil.copy(src, P + dst); return True
    return False
D = []
if cp(R + "report/main.pdf", "report.pdf"):
    D.append(dict(title="Report (LaTeX → PDF)", desc="Full write-up: models, what is fine-tuned and how, data preprocessing, ablations with paired statistics, Blender demo, depth extra credit.", links=[dict(label="open PDF", href="report.pdf")]))
if cp(R + "slides/refocus_slides.pdf", "slides.pdf"):
    cp(R + "slides/refocus_slides.pptx", "slides.pptx"); cp(R + "slides/speaker_notes.md", "slides_notes.md")
    D.append(dict(title="3-slide presentation (3 min)", desc="Problem + approach, results + ablation, demo + extras. Speaker notes timed to 60 s per slide.", links=[dict(label="PDF", href="slides.pdf"), dict(label=".pptx", href="slides.pptx"), dict(label="speaker notes", href="slides_notes.md")]))
if os.path.isdir(R + "viewer"):
    D.append(dict(title="Click-to-refocus viewer", desc="Static web app in D:\\Refocus\\viewer. Click any pixel: the sharpest of 9 frames is shown, with a sharpness-vs-position plot and depth-like map. Run: python -m http.server 8765 in that folder.", links=[dict(label="open demo", href="__VIEWER__", local=True), dict(label="README", href="viewer/README.md")]))
    cp(R + "viewer/README.md", "viewer/README.md")
for mp4 in sorted(glob.glob(R + "remotion/out/*.mp4")):
    n = os.path.basename(mp4); cp(mp4, "remotion/" + n)
    D.append(dict(title="Animation: " + n[:-4], desc="Remotion scene with real sample frames and data.", video="remotion/" + n))
D.append(dict(title="Source repository", desc="Code, report source, citations (credits Tedla et al., SIGGRAPH Asia 2025).", links=[dict(label="GitHub", href="https://github.com/bhavya091213/refocus", local=True), dict(label="Original project", href="https://learn2refocus.github.io/", local=True)]))
json.dump(D, open(P + "deliverables.json", "w"), indent=1); print(len(D), "deliverables")
