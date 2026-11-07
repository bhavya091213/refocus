import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {C, Photo, SHARP, Stage, curve} from './common';

export const FOCAL_DUR = 240;

export const FocalStack: React.FC = () => {
  const frame = useCurrentFrame();
  // sweep focus position 0 -> 8 over frames 30..210
  const pos = interpolate(frame, [30, 210], [0, 8], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const cur = Math.round(pos);
  const pIdx = Math.min(7, Math.floor(interpolate(frame, [30, 210], [0, 8], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}))); // sample point whose winner == pIdx
  const cv = curve(pIdx);
  const pt = SHARP.points[pIdx];
  const gx = 780, gy = 150, gw = 440, gh = 240;
  const path = cv.map((v, i) => `${i ? 'L' : 'M'}${gx + (i / 8) * gw},${gy + gh - v * gh}`).join(' ');
  return (
    <Stage title="A focal stack: 9 photos, 9 focus distances" sub="Position 0 ≈ 5 cm (macro) … position 8 = infinity" dur={FOCAL_DUR}>
      <div style={{position: 'absolute', left: 60, top: 150}}>
        <div style={{position: 'relative'}}>
          <Photo i={cur} w={330} />
          <div style={{position: 'absolute', left: (pt.x / SHARP.w) * 330 - 14, top: (pt.y / SHARP.h) * 462 - 14, width: 28, height: 28, border: `3px solid ${C.warm}`, borderRadius: 14}} />
        </div>
      </div>
      <div style={{position: 'absolute', left: 420, top: 150, width: 320, fontSize: 24, color: C.dim, lineHeight: 1.4}}>
        <div style={{color: C.ink, fontSize: 34, fontWeight: 700}}>Position {cur}</div>
        The ring marks one pixel. Watch it sharpen when the lens focuses at its distance, and blur out again after.
      </div>
      <svg style={{position: 'absolute', left: 0, top: 0}} width={1280} height={720}>
        <rect x={gx} y={gy} width={gw} height={gh} fill={C.panel} rx={8} />
        <path d={path} stroke={C.accent} strokeWidth={4} fill="none" />
        {cv.map((v, i) => <circle key={i} cx={gx + (i / 8) * gw} cy={gy + gh - v * gh} r={i === cur ? 9 : 4} fill={i === cur ? C.warm : C.accent} />)}
        <text x={gx} y={gy - 12} fill={C.dim} fontSize={20}>Sharpness at the ringed pixel (normalised)</text>
        <text x={gx} y={gy + gh + 30} fill={C.dim} fontSize={20}>focus position 0 → 8</text>
      </svg>
      <div style={{position: 'absolute', left: 780, top: 470, width: 440, fontSize: 22, color: C.ink, lineHeight: 1.4}}>
        The sharpest frame at a pixel tells us its depth. That is why one click can pick a frame: <span style={{color: C.warm}}>click → sharpest of 9</span>.
      </div>
      <div style={{position: 'absolute', left: 60, top: 640, display: 'flex', gap: 8}}>
        {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => <Photo key={i} i={i} w={54} style={{outline: i === cur ? `3px solid ${C.warm}` : 'none', opacity: i === cur ? 1 : 0.55, height: 40, objectFit: 'cover'}} />)}
      </div>
    </Stage>
  );
};
