import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import data from './sharpness.json';

export const C = {bg: '#0f1420', panel: '#1a2233', ink: '#e8edf5', dim: '#8d9ab0', accent: '#4cc9f0', warm: '#ffb703', good: '#70e000', bad: '#ff6b6b', violet: '#b388ff'};
export const FONT = 'Segoe UI, Helvetica, Arial, sans-serif';
export const SHARP = data as {w: number; h: number; points: {x: number; y: number; winner: number; sharp: number[]}[]};

export const fade = (frame: number, dur: number, start = 0, len = 15) =>
  interpolate(frame, [start, start + len, dur - len, dur], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

export const useIn = (delay = 0) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: frame - delay, fps, config: {damping: 200}});
};

export const Stage: React.FC<{title: string; sub?: string; children: React.ReactNode; dur: number}> = ({title, sub, children, dur}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: FONT, color: C.ink, opacity: fade(frame, dur)}}>
      <div style={{position: 'absolute', left: 60, top: 36}}>
        <div style={{fontSize: 44, fontWeight: 700}}>{title}</div>
        {sub && <div style={{fontSize: 24, color: C.dim, marginTop: 6}}>{sub}</div>}
      </div>
      {children}
      <div style={{position: 'absolute', left: 60, bottom: 18, fontSize: 16, color: C.dim}}>
        Method: Tedla et al., "Learning to Refocus with Video Diffusion Models", SIGGRAPH Asia 2025 · built on Stable Video Diffusion
      </div>
    </AbsoluteFill>
  );
};

export const Photo: React.FC<{i: number; w?: number; style?: React.CSSProperties}> = ({i, w = 200, style}) => (
  <Img src={staticFile(`frames/f${i}.jpg`)} style={{width: w, height: (w * 560) / 400, objectFit: 'cover', borderRadius: 8, ...style}} />
);

export const Box: React.FC<{x: number; y: number; w: number; h: number; color?: string; label?: string; sub?: string; opacity?: number; fs?: number}> = ({x, y, w, h, color = C.accent, label, sub, opacity = 1, fs = 22}) => (
  <div style={{position: 'absolute', left: x, top: y, width: w, height: h, border: `3px solid ${color}`, background: C.panel, borderRadius: 12, opacity, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', fontSize: fs, padding: 6, boxSizing: 'border-box'}}>
    <div style={{fontWeight: 700}}>{label}</div>
    {sub && <div style={{fontSize: fs * 0.7, color: C.dim, marginTop: 4}}>{sub}</div>}
  </div>
);

/** Normalised sharpness curve (0..1) for one sample point, positions 0..8. */
export const curve = (idx: number) => {
  const s = SHARP.points[idx].sharp;
  const m = Math.max(...s);
  return s.map((v) => v / m);
};
