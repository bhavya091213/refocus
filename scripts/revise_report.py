import io, re
p = "D:/Refocus/report/main.tex"
s = io.open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"; s = s.replace("\r\n", "\n")
def rep(a, b, count=1):
    global s
    assert a in s, "missing: " + a[:80]
    s = s.replace(a, b, count)

# ---------------------------------------------------------------- preamble / title
rep(r"\usepackage{amsmath,amssymb,graphicx,booktabs,hyperref,xcolor,enumitem,listings}",
    r"\usepackage{amsmath,amssymb,graphicx,booktabs,hyperref,xcolor,enumitem,listings,tikz,caption,float}" "\n" r"\usetikzlibrary{arrows.meta,positioning,fit,backgrounds}")
rep("\\newcommand{\\todo}[1]{\\textcolor{red}{[TODO: #1]}}\n\\newcommand{\\tbd}{\\textcolor{red}{\\textbf{TBD}}}\n", "")
rep(r"\author{Bhavya \\ \textit{Final project, course name \todo{fill in}}}", r"\author{Bhavya \\ \textit{Final project}}")

# ---------------------------------------------------------------- abstract
a = s.index(r"\begin{abstract}"); b = s.index(r"\end{abstract}") + len(r"\end{abstract}")
s = s[:a] + r"""\begin{abstract}
Given one photograph with an arbitrary focus setting, we want to produce a \emph{focal stack}---the same scene
at nine focus distances---so that a user can click any pixel and bring it into focus.
We follow Tedla et al.~\cite{tedla2025refocus}, who treat a focal stack as a video and fine-tune
Stable Video Diffusion~\cite{blattmann2023svd} on a smartphone focal-stack dataset.
We (i) reproduce their pipeline and evaluate their released checkpoint, (ii) fine-tune the same
model ourselves on a small budget (4{,}000 steps, about \$54 of cloud GPU time), and (iii) run a controlled ablation of how the input photo and its focus position are presented to the network.
On a fixed 20-scene test subset the authors' 200k-step checkpoint reaches PSNR 31.07 and LPIPS 0.160; our three arms reach PSNR 28.6--29.1.
Comparing the arms on identical items, the two ``slot-based'' schemes (the authors' \texttt{random} mode and \texttt{ablate\_position}) beat encoding the position through \texttt{motion\_bucket\_id}
(+0.49\,dB for the best, 55 of 60 items), while \texttt{random} versus \texttt{ablate\_position} is a trade-off between PSNR and SSIM/LPIPS.
Beyond the reproduction we measure that monocular depth agrees with focus (Spearman $\rho=-0.80$ on real stacks), render ground-truth focal stacks in Blender to probe the released model, and ship a click-to-refocus web viewer with a live photo-to-stack generator.
\end{abstract}""" + s[b:]

# ---------------------------------------------------------------- related work (new, before Problem statement's end -> after Problem statement)
rep(r"\section{Background and model choices}", r"""\section{Related work}
\textbf{Refocusing and depth of field.} Light-field cameras capture the information needed to refocus after the fact~\cite{ng2005lightfield}; single-image approaches instead estimate depth and re-render blur, as in the portrait-mode pipeline of Wadhwa et al.~\cite{wadhwa2018synthetic}.
These methods can add blur but cannot remove it. Removing defocus blur from a single image has been studied with dual-pixel sensors~\cite{abuolaim2020defocus}, which again needs special data.
\textbf{Generative approach.} Latent diffusion~\cite{rombach2022ldm} made high-resolution generative modelling affordable, and video diffusion models such as Stable Video Diffusion~\cite{blattmann2023svd} add temporal layers that keep frames consistent. Tedla et al.~\cite{tedla2025refocus} observe that a focal stack is a video whose ``time'' axis is focus distance and fine-tune SVD on 1{,}637 smartphone focal stacks; this is the work we reproduce.
\textbf{Why we still ran an ablation.} The paper fixes one way of presenting the input and its focus position to the network; the code also contains alternatives. A short, controlled comparison tells us how much of the behaviour depends on that choice.

\section{Background and model choices}""")

# ---------------------------------------------------------------- architecture figure + parameter counts
rep(r"\todo{add architecture figure (TikZ) showing VAE / CLIP / U-Net and where the conditioning enters}", r"""
\begin{figure}[t]\centering
\begin{tikzpicture}[node distance=7mm and 9mm, font=\footnotesize,
  blk/.style={draw, rounded corners=2pt, minimum height=8mm, align=center, inner sep=3pt},
  frz/.style={blk, fill=blue!8}, trn/.style={blk, fill=orange!25}, io/.style={blk, fill=gray!10},
  ar/.style={-{Stealth[length=2mm]}, thick}]
  \node[io] (img) {input photo $I_k$\\ (position $k$)};
  \node[frz, right=of img, yshift=7mm] (vae) {VAE encoder\\ (frozen)};
  \node[frz, right=of img, yshift=-7mm] (clip) {CLIP image\\ encoder (frozen)};
  \node[blk, right=of vae] (slot) {place latent in\\ slot $k$ of 9,\\ other slots $=0$};
  \node[blk, right=of slot] (cat) {concat with\\ noisy latent\\ (4+4 = 8 ch)};
  \node[trn, right=of cat, minimum height=14mm] (unet) {U-Net\\ spatial layers frozen\\ \textbf{temporal blocks trained}};
  \node[frz, right=of unet] (dec) {VAE decoder\\ (frozen)};
  \node[io, right=of dec] (out) {9-frame\\ focal stack};
  \draw[ar] (img) -- (vae); \draw[ar] (img) -- (clip);
  \draw[ar] (vae) -- (slot); \draw[ar] (slot) -- (cat); \draw[ar] (cat) -- (unet); \draw[ar] (unet) -- (dec); \draw[ar] (dec) -- (out);
  \draw[ar] (clip) -| node[pos=0.25, below] {cross-attention} (unet.south);
  \node[blk, above=5mm of cat] (noise) {noise $\sigma\epsilon$\\ on 9 latents};
  \draw[ar] (noise) -- (cat);
\end{tikzpicture}
\caption{Model overview. Blue = frozen, orange = trained. The slot of the non-zero latent tells the network the input's focus position (arm A; arms B and C copy the latent to all slots, see Section~\ref{sec:ablation}). At inference the noisy latent is denoised for 25 steps and decoded to nine frames.}\label{fig:arch}
\end{figure}""")
rep(r"\todo{report exact trainable parameter count / percentage once measured on the GPU}", r"""
\textbf{Measured parameter counts.} We loaded the released checkpoint and counted parameters (script run on the cloud machine, CPU only): the U-Net has \textbf{1{,}524.6\,M} parameters, of which \textbf{397.6\,M (26.1\%)} belong to \texttt{temporal\_transformer\_block} modules and are the only ones trained; the CLIP image encoder has 632.1\,M and the VAE 97.7\,M (both frozen), so the whole pipeline has about 2.25\,B parameters. The U-Net's first convolution takes 8 input channels (4 noisy + 4 conditioning), confirming the concatenation scheme. On disk, the authors' checkpoint plus the SVD base parts are about 8.3\,GB.""")

# ---------------------------------------------------------------- hyperparameter table: add paper values + discrepancy paragraph
rep(r"""Checkpoint released by authors & 200{,}000 steps\\
\bottomrule\end{tabular}
\end{table}""", r"""Checkpoint released by authors & 200{,}000 steps\\
\bottomrule\end{tabular}
\end{table}
\textbf{Paper versus repository defaults.} The paper (Sec.\ 5.1) states a different recipe from the repository's default configuration: ``learning rate of 0.0004'', batch size 4, an EMA with decay $10^{-5}$, 200{,}000 training iterations (it says ``epochs''), and a classifier-free-guidance weight of 1.5 at test time; it does not state the hardware. We could not tell which recipe produced the released checkpoint, so we ran the configuration shipped in the repository ($2\times10^{-5}$ effective learning rate, global batch 2, no EMA). Our learning rate is therefore about $20\times$ smaller than the paper's, which, together with 2\% of the steps, is a likely reason for the gap to the released checkpoint in Section~\ref{sec:results}; we did not test this.""")

# ---------------------------------------------------------------- data section
rep(r"""\todo{capture device, licence of the dataset}""", r"""
\textbf{Capture device and licence.} According to the paper (Sec.\ 3.1) the data were captured with a custom rig of five iPhones (an iPhone 12 is named in the introduction; the exact model of each phone is not given); each phone records a focal stack by moving the focus from its minimum to maximum distance in nine steps, which in the iPhone API correspond to focus values 0 to 0.8 in steps of 0.1. Only the central camera's stack is used for training. The paper reports 1{,}637 scenes (1{,}474 training, 163 test); the archive we verified contains 1{,}643 scene folders (1{,}638 complete) and a 164-scene test list, so our counts differ from the paper's by one to six scenes, which we did not investigate. We found \emph{no stated licence} for the dataset on the project page, the repository or the paper's abstract page, so we used it only for this coursework, did not redistribute it, and keep it out of our public repository.""")
rep(r"""\todo{augmentation: none observed in code; confirm}""", r"""We searched \texttt{training/utils.py} and \texttt{training/svd_runner.py} for flips, crops, colour jitter and similar operations and found none (the dataset class sets \texttt{do\_center\_crop=False}); the only randomness is the shuffling of scenes and the random choice of the input frame $k$ in conditioning mode \texttt{random}. We therefore did no augmentation either.""")

# ---------------------------------------------------------------- evaluation protocol: uncertainty paragraph
a = s.index(r"\textbf{Uncertainty.} Standard errors over the 480")
b = s.index(r"\subsection{Baseline: authors' released checkpoint}")
s = s[:a] + r"""\textbf{Uncertainty.} The evaluation produces 60 items per model (20 scenes $\times$ 3 input positions). We first average each metric over the 8 non-input frames of an item and report the mean and the standard error over the 60 items (the frame-level standard error is about half as large because frames of one generation are strongly correlated, so we do not use it). The three items of one scene share content, so even the item-level error is slightly optimistic. Because every model is evaluated on exactly the same items, we also report \emph{paired} differences, which remove the large scene-to-scene variation; Section~\ref{sec:results} uses both.

""" + s[b:]

# ---------------------------------------------------------------- results table + new results subsections
a = s.index(r"\begin{table}[h]\centering" + "\n" + r"\caption{Test-subset results")
b = s.index(r"\subsection{Pipeline check}")
res = r"""\subsection{Results}\label{sec:results}
\begin{table}[h]\centering
\caption{Test-subset results (20 scenes $\times$ input positions 1, 4, 7; mean over the 8 non-input frames of each of the 60 items; $\pm$ = standard error over items). Bold = best of our three arms.}\label{tab:results}
\begin{tabular}{lcccc}\toprule
Model & PSNR$\uparrow$ & SSIM$\uparrow$ & LPIPS$\downarrow$ & depth-$\rho$ ($\downarrow$)\\\midrule
Authors' 200k checkpoint & $31.07\pm0.22$ & $0.893\pm0.004$ & $0.160\pm0.004$ & $-0.70\pm0.04$\\
A: \texttt{random} (ours, 4k steps) & $28.76\pm0.23$ & $\mathbf{0.870}\pm0.005$ & $\mathbf{0.192}\pm0.004$ & $-0.61\pm0.05$\\
B: \texttt{ablate\_position} (ours) & $\mathbf{29.11}\pm0.28$ & $0.863\pm0.005$ & $0.196\pm0.005$ & $-0.58\pm0.05$\\
C: \texttt{ablate\_time} (ours) & $28.62\pm0.29$ & $0.858\pm0.005$ & $0.199\pm0.005$ & $-0.61\pm0.04$\\
Real stacks (reference) & -- & -- & -- & $-0.76$\\
\bottomrule\end{tabular}\end{table}
\begin{figure}[t]\centering\includegraphics[width=\linewidth]{fig_results.pdf}
\caption{The headline metrics with item-level standard-error bars. The vertical axes are truncated (the start value is printed under each panel), which exaggerates small differences; the large gap to the authors' checkpoint is real, the differences among our three arms are much smaller than the error bars.}\label{fig:results}\end{figure}
Unpaired, the three arms overlap within about one to two standard errors on every metric, so the table alone would suggest that no conditioning scheme stands out. The authors' checkpoint is clearly better (PSNR $+2.0$ to $+2.5$\,dB, LPIPS $-0.03$ to $-0.04$).

\subsection{Paired comparison of the arms}
Since all models are scored on the same 60 items, the per-item difference between two models cancels most scene difficulty. Figure~\ref{fig:paired} shows the mean paired difference with a 95\% interval ($\pm1.98$ standard errors of the difference), and Table~\ref{tab:paired} gives the numbers.
\begin{figure}[t]\centering\includegraphics[width=\linewidth]{fig_paired.pdf}
\caption{Paired differences between models over the same 60 items, with 95\% intervals. For PSNR and SSIM positive means the first model is better; for LPIPS negative means the first model is better. The three input positions of a scene are not independent, so the intervals are slightly too narrow.}\label{fig:paired}\end{figure}
\begin{table}[h]\centering
\caption{Paired differences (first minus second), items where the first model scores higher, and $t=$ mean/s.e.}\label{tab:paired}
\begin{tabular}{lccc}\toprule
Comparison & $\Delta$PSNR (dB) & $\Delta$SSIM & $\Delta$LPIPS\\\midrule
B $-$ C & $+0.49$ (55/60, $t=8.4$) & $+0.005$ ($t=5.7$) & $-0.003$ ($t=-4.9$)\\
A $-$ C & $+0.14$ (32/60, $t=1.3$) & $+0.013$ (50/60, $t=6.7$) & $-0.008$ ($t=-3.4$)\\
A $-$ B & $-0.35$ (18/60, $t=-3.0$) & $+0.008$ (44/60, $t=4.3$) & $-0.005$ ($t=-2.2$)\\
Authors $-$ A & $+2.31$ (58/60, $t=16.3$) & $+0.023$ ($t=10.7$) & $-0.031$ ($t=-20.1$)\\
\bottomrule\end{tabular}\end{table}
Reading the table: B beats C on all three metrics and wins 55 of 60 items on PSNR. A beats C on SSIM and LPIPS but not on PSNR. A and B trade places: B has higher PSNR, A has higher SSIM and lower LPIPS. So \texttt{motion\_bucket\_id} (C) is the weakest way to give the position, while A and B are close.

\subsection{Error versus distance from the input}
Figure~\ref{fig:dist} splits PSNR by the distance between the target position and the input position. For every model the error rises with that distance: arm A falls from 30.0\,dB at distance 1 to 27.7\,dB at distance 7, and the authors' checkpoint from 31.9 to 30.7\,dB. This is what one expects when the model has to hallucinate more blur or more detail the further it moves from what it was given. The curves of our three arms are almost parallel, so no arm is better at ``far'' extrapolation.
\begin{figure}[t]\centering\includegraphics[width=\linewidth]{fig_dist.pdf}
\caption{Left: PSNR against the distance between target and input positions. Right: PSNR by target position (inputs 1, 4 and 7 pooled; target positions equal to an input position have fewer samples).}\label{fig:dist}\end{figure}

\subsection{Training loss}
Figure~\ref{fig:loss} shows the logged loss. It is the mean squared error of one randomly noised sample per step, so single values are very noisy and the large swings (about 0.07 to 0.28) reflect which noise levels and scenes were drawn, not instability. The three arms nearly coincide because they all use seed 0 and therefore see the same scenes and noise levels at each step; as a result the loss is \emph{not} a measure of quality and cannot separate the arms, which is why we compare them on held-out metrics. All arms end near 0.07.
\begin{figure}[t]\centering\includegraphics[width=\linewidth]{fig_loss.pdf}
\caption{Training loss of the three arms (logged every 20 steps). Left: 15-point moving average. Right: mean in 1000-step blocks.}\label{fig:loss}\end{figure}

\subsection{Qualitative comparison}
Figure~\ref{fig:qual} shows one test scene with the input at position 4. At this size (180$\times$252 px per frame in our saved evaluation sheets) the models' outputs look close to the real stack: the global appearance and the gradual change of sharpness are preserved, and differences between arms are not visible by eye, which agrees with the small metric differences. We did not save full-resolution generations for all 240 items, so a more careful qualitative study is left out.
\begin{figure}[t]\centering\includegraphics[width=\linewidth]{fig_qual.pdf}
\caption{Real stack (top) and the models' generated stacks (input photo at position 4) for one test scene.}\label{fig:qual}\end{figure}

\subsection{PSNR by input position}
\begin{table}[h]\centering
\caption{PSNR (dB) by input position (mean over 20 scenes $\times$ 8 target frames).}
\begin{tabular}{lccc}\toprule
Model & input 1 & input 4 & input 7\\\midrule
Authors' 200k & 30.69 & 31.46 & 31.05\\
A: \texttt{random} & 28.28 & 29.11 & 28.89\\
B: \texttt{ablate\_position} & 28.65 & 29.41 & 29.25\\
C: \texttt{ablate\_time} & 28.20 & 28.93 & 28.72\\
\bottomrule\end{tabular}\end{table}
A middle input (position 4) is easiest for every model, which is natural because it is on average closest to the other eight positions.

"""
s = s[:a] + res + s[b:]

# ---------------------------------------------------------------- compute budget: tidy
# ---------------------------------------------------------------- click-to-refocus section
a = s.index(r"\section{Click-to-refocus interface}\label{sec:ui}")
b = s.index(r"\section{Extra credit: depth and focus (exploration)}")
ui = r"""\section{Click-to-refocus interface and demo system}\label{sec:ui}
\textbf{Selecting the frame.} Given a generated stack, define the local sharpness of frame $j$ around pixel $p$ as the variance of the Laplacian in a window $W_p$: $s_j(p)=\mathrm{Var}_{q\in W_p}[\nabla^2 \hat I_j(q)]$. Clicking $p$ displays $\hat I_{j^\star}$ with $j^\star=\arg\max_j s_j(p)$.
We implemented this in a dependency-free web page (HTML/JavaScript, \texttt{viewer/}); all sharpness computation happens in the browser on a downsampled grayscale copy of the frames (width at most 256\,px), using integral images of the Laplacian and its square so that the window statistics of any click are computed in constant time. The page cross-fades between frames, shows a position slider and a strip of the nine frames, plots $s_j(p)$ for the clicked point, and can colour every coarse cell by its sharpest frame (a ``depth-like map'').
Figure~\ref{fig:ui} shows the viewer on our Blender macro scene, where by construction the duck, apple, bust and cat are sharpest at positions 4, 5, 6 and 7: clicks on the duck and on the cat select positions 4 and 7, and clicks on the apple and the bust (not shown) select 5 and 6.
\begin{figure}[t]\centering\includegraphics[width=\linewidth]{fig_ui.png}
\caption{The click-to-refocus viewer on the Blender macro stack. Left to right: click on the duck (position 4); click on the cat (position 7); the depth-like map (cool colours = sharpest at far positions; grey = too little texture); a click on the flat floor, where the viewer warns that the choice is unreliable.}\label{fig:ui}\end{figure}
\textbf{Failure case: textureless regions.} Where an area has no texture (a plain table, a wall, the sky) all nine frames have nearly the same Laplacian variance, so the argmax is dominated by noise. The viewer detects this by comparing the maximum and minimum sharpness across the nine frames and shows a ``low-texture spot, choice unreliable'' warning instead of presenting the choice as confident (right panel of Figure~\ref{fig:ui}); the depth-like map leaves such cells grey. A better rule would propagate the decision from nearby textured pixels of the same object, which we did not implement. The same weakness limits our depth-consistency metric, which is why that metric only uses the 40\% most textured pixels.

\textbf{Photo-to-stack generator.} The page also lets the user take or choose a photo and generate a stack with the model (Figure~\ref{fig:system}). The browser downsizes the photo to at most 1600\,px and sends it to our dashboard server, which forwards it over an SSH tunnel to a small HTTP server on a rented 24\,GB A10 GPU. That server keeps the model loaded and handles one request at a time. To fit 24\,GB we keep the weights in fp32 but run the forward pass under bf16 autocast and decode the video latents two frames at a time; this uses about 19\,GB, and one $576\times832$ photo takes about 48\,s. The image is resized so that it has at most 500{,}000 pixels, as in the authors' code, and the user states whether the photo is focused near (position 1), mid (4) or far (7), which selects the input slot. We checked the whole chain end to end on a rendered Blender photo, where it produced a plausible near-to-far sweep (the cat and bust sharpen towards the far positions); we did not evaluate its quality beyond that, and the numbers in Table~\ref{tab:results} come from the full-precision authors' pipeline, not from this reduced-memory one.
\begin{figure}[t]\centering
\begin{tikzpicture}[node distance=8mm, font=\footnotesize, blk/.style={draw, rounded corners=2pt, minimum height=8mm, align=center, inner sep=3pt}, ar/.style={-{Stealth[length=2mm]}, thick}]
  \node[blk] (ph) {phone / browser\\ (viewer page)};
  \node[blk, right=12mm of ph] (dash) {dashboard server\\ (this PC, behind a\\ Cloudflare tunnel)};
  \node[blk, right=12mm of dash] (gpu) {GPU server\\ (A10, SSH tunnel)\\ model stays loaded};
  \draw[ar] (ph) -- node[above]{photo} (dash); \draw[ar] (dash) -- node[above]{job} (gpu);
  \draw[ar] (gpu.south) -- ++(0,-6mm) -| node[pos=0.25, below]{9 frames} (dash.south);
  \draw[ar] (dash.north) -- ++(0,6mm) -| node[pos=0.25, above]{poll, then show} (ph.north);
\end{tikzpicture}
\caption{System behind the photo-to-stack demo. The GPU machine is only switched on while testing; when it is off, the page says so.}\label{fig:system}\end{figure}
Privacy: the generator sends the user's photo to a cloud GPU, which the page states; uploads of ready-made nine-frame stacks are processed entirely in the browser.

"""
s = s[:a] + ui + s[b:]

# ---------------------------------------------------------------- limitations tidy
rep(r"""\textbf{Other limitations.} Evaluation covers 20 scenes and three input positions; no FID or VIF; the position-to-distance mapping for the Blender demo is our assumption; we did not keep the 25\,GB trained checkpoints (the instance was terminated), so the live demo uses the authors' released weights.""",
    r"""\textbf{Other limitations.} Evaluation covers 20 scenes and three input positions; no FID or VIF; one seed per arm; the position-to-distance mapping for the Blender demo is our assumption; the learning rate we used is the repository's, not the paper's (Section~3); and the photo generator runs in reduced precision, which we did not quantify. The licence of the dataset is not stated, so we do not redistribute it.""")
rep(r"""\textbf{What we can and cannot say.}""", r"""\textbf{What the comparison says.}""")

# ---------------------------------------------------------------- bibliography
rep(r"\end{thebibliography}", r"""\bibitem{ng2005lightfield} R.~Ng, M.~Levoy, M.~Br\'edif, G.~Duval, M.~Horowitz, P.~Hanrahan. \emph{Light Field Photography with a Hand-held Plenoptic Camera}. Stanford Tech Report CTSR 2005-02, 2005.
\bibitem{wadhwa2018synthetic} N.~Wadhwa et al. \emph{Synthetic Depth-of-Field with a Single-Camera Mobile Phone}. ACM Transactions on Graphics (SIGGRAPH), 2018.
\bibitem{abuolaim2020defocus} A.~Abuolaim, M.~S.~Brown. \emph{Defocus Deblurring Using Dual-Pixel Data}. ECCV, 2020.
\bibitem{rombach2022ldm} R.~Rombach, A.~Blattmann, D.~Lorenz, P.~Esser, B.~Ommer. \emph{High-Resolution Image Synthesis with Latent Diffusion Models}. CVPR, 2022.
\bibitem{zhang2018lpips} R.~Zhang, P.~Isola, A.~Efros, E.~Shechtman, O.~Wang. \emph{The Unreasonable Effectiveness of Deep Features as a Perceptual Metric}. CVPR, 2018.
\bibitem{wang2004ssim} Z.~Wang, A.~Bovik, H.~Sheikh, E.~Simoncelli. \emph{Image Quality Assessment: From Error Visibility to Structural Similarity}. IEEE TIP, 2004.
\end{thebibliography}""")
rep(r"\begin{thebibliography}{9}", r"\begin{thebibliography}{99}")
rep(r"LPIPS (VGG backbone, as in the authors' script)", r"LPIPS~\cite{zhang2018lpips} (VGG backbone, as in the authors' script)")
rep(r"PSNR and SSIM (torchmetrics, data range 1)", r"PSNR and SSIM~\cite{wang2004ssim} (torchmetrics, data range 1)")

io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl)); print("ok")
