import io
p = "D:/Refocus/report/main.tex"
s = io.open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"; s = s.replace("\r\n", "\n")
a = s.index("\\textbf{Results.} The authors' 200k-step")
b = s.index("\\textbf{Other limitations.}")
new = (
"\\textbf{Results.} The authors' 200k-step checkpoint is clearly best on every metric (PSNR 31.07 vs.\\ 28.6--29.1). That is expected: our arms saw 2\\% of its training steps with a global batch of 2. A paired comparison over the same 60 items (mean over the 8 non-input frames of each item) gives it a 2.31\\,dB PSNR lead over arm A, winning 58 of 60 items.\n\n"
"\\textbf{Comparing our three arms (paired).} Standard errors of the table treat each model separately and hide that all models are scored on the same items; pairing removes the scene-to-scene variation. With paired differences (mean difference, items won, $t=$ mean/s.e.; the three input positions of a scene are not independent, so $t$ is only a rough guide):\n"
"\\begin{itemize}\\itemsep0pt\n"
"\\item B vs.\\ C: B is better on all three metrics, PSNR $+0.49$\\,dB (55 of 60 items, $t=8.4$), SSIM $+0.005$, LPIPS $-0.003$. Encoding the position through \\texttt{motion\\_bucket\\_id} (C) is the weakest scheme here.\n"
"\\item A vs.\\ C: A is better on SSIM ($+0.013$, 50 of 60) and LPIPS ($-0.008$), and about equal on PSNR ($+0.14$\\,dB, $t=1.3$).\n"
"\\item A vs.\\ B: a trade-off. B has higher PSNR ($+0.35$\\,dB, $t=3.0$), A has higher SSIM ($+0.008$, $t=4.3$) and lower LPIPS ($-0.005$, $t=2.2$ in A's favour).\n"
"\\end{itemize}\n"
"The depth-consistency score is similar for all arms ($-0.58$ to $-0.61$) and below the authors' $-0.70$; real stacks reach $-0.76$. Error also grows with the distance between the input position and the target position: for arm A, PSNR falls from 30.0\\,dB at distance 1 to 27.7\\,dB at distance 7, and the authors' checkpoint shows the same trend (31.9 to 30.7).\n\n"
"\\textbf{What we can and cannot say.} Knowing the position matters less than \\emph{how} it is given: the slot-based schemes (A and B) both beat the \\texttt{motion\\_bucket\\_id} scheme (C). Whether the model should be told the position at all (A vs.\\ B) is a perceptual-versus-pixel trade-off that we cannot settle: B favours PSNR, A favours SSIM and LPIPS. These are single-seed results at 4{,}000 steps on 20 scenes, so a ranking could change with longer training or other seeds.\n\n")
s = s[:a] + new + s[b:]
old = "At 4{,}000 steps none of the three is clearly better than the others, and all trail"
assert old in s
s = s.replace(old, "At 4{,}000 steps the slot-based schemes (\\texttt{random}, \\texttt{ablate\\_position}) beat the \\texttt{motion\\_bucket\\_id} scheme, while \\texttt{random} vs.\\ \\texttt{ablate\\_position} is a PSNR-versus-SSIM/LPIPS trade-off, and all three trail")
old2 = "with no clear winner among them."
assert old2 in s
s = s.replace(old2, "with the \\texttt{motion\\_bucket\\_id} variant the weakest.")
io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl)); print("ok")
