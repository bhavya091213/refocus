"""Repair table rows in the Experiments section whose '\\\\' line breaks were halved to '\\' by a shell heredoc."""
import io, re
p = "D:/Refocus/report/main.tex"
s = io.open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")
a = s.index("\\section{Experiments}"); b = s.index("\\section{Click-to-refocus interface}")
sec = s[a:b]
BS = "\\"
out = []
for ln in sec.split("\n"):
    t = ln.rstrip()
    in_tab = ("&" in t) or t.startswith("Mode &") or t.startswith("Model &")
    # header row followed by \midrule on the same line, written as 'X\\midrule' (should be 'X\\\midrule')
    t = t.replace(BS + BS + "midrule", BS + BS + BS + "midrule")
    t = t.replace(BS + BS + "toprule", BS + BS + BS + "toprule")
    # data rows: a table row that ends with a single backslash needs two
    if in_tab and t.endswith(BS) and not t.endswith(BS + BS):
        t = t + BS
    out.append(t)
sec2 = "\n".join(out)
io.open(p, "w", encoding="utf-8", newline="").write((s[:a] + sec2 + s[b:]).replace("\n", nl))
print("fixed")
