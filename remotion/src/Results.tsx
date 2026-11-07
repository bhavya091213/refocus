import React from 'react';
import {C, Stage, useIn} from './common';

export const RES_DUR = 270;

const ROWS = [
  {n: "Authors' 200k", p: 31.07, s: 0.893, l: 0.16, c: C.good},
  {n: 'A random', p: 28.76, s: 0.87, l: 0.192, c: C.accent},
  {n: 'B ablate_position', p: 29.11, s: 0.863, l: 0.196, c: C.violet},
  {n: 'C ablate_time', p: 28.62, s: 0.858, l: 0.199, c: C.warm},
];

const Panel: React.FC<{title: string; vals: number[]; lo: number; hi: number; fmt: (v: number) => string; delay: number; better: string}> = ({title, vals, lo, hi, fmt, delay, better}) => {
  const t = useIn(delay);
  return (
    <div style={{width: 380}}>
      <div style={{fontSize: 26, fontWeight: 700}}>{title} <span style={{fontSize: 16, color: C.dim}}>{better}</span></div>
      {ROWS.map((r, i) => (
        <div key={r.n} style={{marginTop: 18}}>
          <div style={{fontSize: 16, color: C.dim}}>{r.n}</div>
          <div style={{display: 'flex', alignItems: 'center', gap: 10}}>
            <div style={{height: 28, width: Math.max(4, ((vals[i] - lo) / (hi - lo)) * 300 * t), background: r.c, borderRadius: 5}} />
            <div style={{fontSize: 20}}>{fmt(vals[i])}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

export const Results: React.FC = () => {
  const note = useIn(120);
  return (
    <Stage title="Results: 20 test scenes × 3 input positions" sub="Authors' fully trained model vs our three 4,000-step ablation arms" dur={RES_DUR}>
      <div style={{position: 'absolute', left: 60, top: 150, display: 'flex', gap: 40}}>
        <Panel title="PSNR" better="higher is better" vals={ROWS.map((r) => r.p)} lo={27} hi={31.5} fmt={(v) => v.toFixed(2)} delay={10} />
        <Panel title="SSIM" better="higher is better" vals={ROWS.map((r) => r.s)} lo={0.85} hi={0.9} fmt={(v) => v.toFixed(3)} delay={30} />
        <Panel title="LPIPS" better="lower is better · bar inverted" vals={ROWS.map((r) => 0.21 - r.l)} lo={0} hi={0.06} fmt={(v) => (0.21 - v).toFixed(3)} delay={50} />
      </div>
      <div style={{position: 'absolute', left: 60, top: 590, width: 1160, fontSize: 22, color: C.ink, opacity: note, lineHeight: 1.4}}>
        Authors' checkpoint trained 50× longer and wins. Among our arms there is no clear winner: B has the best PSNR, A the best SSIM/LPIPS, C is last.
        <span style={{color: C.dim}}> (Bar axes are truncated to show differences; LPIPS bars are inverted, longer = better.)</span>
      </div>
    </Stage>
  );
};
