"""Insert report/_blender_section.tex before the Click-to-refocus section (idempotent) and copy figures into report/."""
import io, shutil
SCR = "C:/Users/Raj/AppData/Local/Temp/claude/C--Windows-System32/960471f0-c3ff-421f-8954-03a25a2a9522/scratchpad/"
for src, dst in (("sharp_curves.png", "sharp_curves.png"), ("compare_macro_in4.jpg", "compare_macro_in4.jpg"), ("macro_curves.png", "macro_curves.png")):
    shutil.copy(SCR + src, "D:/Refocus/report/" + dst)
p = "D:/Refocus/report/main.tex"
s = io.open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"; s = s.replace("\r\n", "\n")
sec = io.open("D:/Refocus/report/_blender_section.tex", encoding="utf-8", newline="").read().replace("\r\n", "\n")
if "sec:blender" in s:
    a = s.index("\\section{Synthetic demo"); b = s.index("\\section{Click-to-refocus interface}"); s = s[:a] + s[b:]   # replace existing
marker = "\\section{Click-to-refocus interface}"
s = s.replace(marker, sec + marker, 1)
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl)); print("section inserted")
