import io
p = "D:/Refocus/report/main.tex"
s = io.open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"; s = s.replace("\r\n", "\n")
def rep(a, b):
    global s
    assert a in s, a[:50]
    s = s.replace(a, b)
rep("Authors' 200k checkpoint & \\tbd & \\tbd & \\tbd & \\tbd\\\\", "Authors' 200k checkpoint & $31.07\\pm0.14$ & $0.893\\pm0.003$ & $0.160\\pm0.002$ & $-0.70$\\\\")
rep("Real stacks (reference) & -- & -- & -- & \\tbd\\\\", "Real stacks (reference) & -- & -- & -- & $-0.76$\\\\")
rep("mean $\\pm$ s.e.). \\tbd}", "mean $\\pm$ s.e.). Rows A--C: all three arms finished training (4{,}000 steps); their held-out evaluation was still running when this version was compiled.}")
for a in ("A: \\texttt{random} (ours, 4k steps)", "B: \\texttt{ablate\\_position} (ours)", "C: \\texttt{ablate\\_time} (ours)"):
    rep(a + " & \\tbd & \\tbd & \\tbd & \\tbd\\\\", a + " & \\multicolumn{4}{c}{\\emph{evaluation running}}\\\\")
rep("\\tbd{total hours and dollars spent, against the \\$100 cap}", "Status at compile time: each arm trained 4{,}000 steps in about 1\\,h\\,58\\,min (1.77\\,s/step); the authors' checkpoint evaluation took 72\\,min. Final hours and dollars will be added when the three arm evaluations finish, against the \\$100 cap.")
rep("\\section{Limitations and discussion}\n\\tbd", "\\section{Limitations and discussion}\nTo be written once the arm evaluations finish. Already known: our arms use 2\\% of the authors' training steps and a global batch of 2, so they are expected to trail the 200k checkpoint; the ablation compares conditioning schemes under that short budget only; evaluation covers 20 scenes $\\times$ 3 input positions.")
rep("\\section{Conclusion}\n\\tbd", "\\section{Conclusion}\nTo be completed with the ablation outcome.")
rep("\\tbd{one-sentence headline result}.", "Headline result pending: the authors' checkpoint scores PSNR 31.07, SSIM 0.893, LPIPS 0.160 on our test subset; the three ablation arms are being evaluated.")
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl)); print("ok")
