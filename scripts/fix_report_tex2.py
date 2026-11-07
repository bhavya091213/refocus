import io
p = "D:/Refocus/report/main.tex"
s = io.open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"; s = s.replace("\r\n", "\n")
s = s.replace(r"\texttt{training/utils.py} and \texttt{training/svd_runner.py}", r"\texttt{training/utils.py} and \texttt{training/svd\_runner.py}")
s = s.replace(r"\texttt{do\_center\_crop=False}", r"\texttt{do\_center\_crop=False}")
s = s.replace(r"\begin{tikzpicture}[node distance=7mm and 9mm,", r"\resizebox{\linewidth}{!}{\begin{tikzpicture}[node distance=7mm and 9mm,")
s = s.replace(r"\node[blk, above=5mm of cat] (noise) {noise $\sigma\epsilon$\\ on 9 latents};" + "\n" + r"  \draw[ar] (noise) -- (cat);" + "\n" + r"\end{tikzpicture}", r"\node[blk, above=5mm of cat] (noise) {noise $\sigma\epsilon$\\ on 9 latents};" + "\n" + r"  \draw[ar] (noise) -- (cat);" + "\n" + r"\end{tikzpicture}}")
s = s.replace(r"\begin{tikzpicture}[node distance=8mm, font=\footnotesize,", r"\resizebox{\linewidth}{!}{\begin{tikzpicture}[node distance=8mm, font=\footnotesize,")
s = s.replace(r"  \draw[ar] (dash.north) -- ++(0,6mm) -| node[pos=0.25, above]{poll, then show} (ph.north);" + "\n" + r"\end{tikzpicture}", r"  \draw[ar] (dash.north) -- ++(0,6mm) -| node[pos=0.25, above]{poll, then show} (ph.north);" + "\n" + r"\end{tikzpicture}}")
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl)); print("ok")
