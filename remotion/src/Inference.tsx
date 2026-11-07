import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {Box, C, Photo, SHARP, Stage, useIn} from './common';

export const INF_DUR = 300;

export const Inference: React.FC = () => {
  const frame = useCurrentFrame();
  const a = useIn(10), b = useIn(60);
  // three demo clicks, each lands on a different object
  const clicks = [3, 5, 1].map((i) => SHARP.points[i]);
  const ci = frame < 150 ? 0 : frame < 215 ? 1 : 2;
  const click = clicks[ci];
  const shown = frame < 120 ? 4 : click.winner;
  const W = 300, H = 420;
  return (
    <Stage title="Click-to-refocus" sub="One photo in → 9-frame focal stack out → a click selects the sharpest frame at that pixel" dur={INF_DUR}>
      <div style={{position: 'absolute', left: 60, top: 150, opacity: a}}>
        <Photo i={4} w={150} />
        <div style={{fontSize: 18, color: C.dim, marginTop: 6}}>your photo</div>
      </div>
      <Box x={250} y={210} w={170} h={90} label="Video diffusion" sub="25 denoising steps" opacity={a} />
      <div style={{position: 'absolute', left: 450, top: 160, display: 'grid', gridTemplateColumns: 'repeat(3, 84px)', gap: 6, opacity: b}}>
        {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => <Photo key={i} i={i} w={84} style={{outline: i === shown ? `3px solid ${C.warm}` : 'none', height: 112, objectFit: 'cover'}} />)}
      </div>
      <div style={{position: 'absolute', left: 450, top: 560, fontSize: 18, color: C.dim, opacity: b}}>generated stack (positions 0–8)</div>
      <div style={{position: 'absolute', left: 840, top: 150, opacity: b}}>
        <div style={{position: 'relative', width: W, height: H}}>
          <Photo i={shown} w={W} />
          {frame > 120 && (
            <div style={{position: 'absolute', left: (click.x / SHARP.w) * W - 18, top: (click.y / SHARP.h) * H - 18, width: 36, height: 36, borderRadius: 18, border: `3px solid ${C.warm}`, background: 'rgba(255,183,3,0.25)', transform: `scale(${interpolate((frame - 120) % 65, [0, 12], [1.6, 1], {extrapolateRight: 'clamp'})})`}} />
          )}
        </div>
        <div style={{fontSize: 22, marginTop: 8, color: C.warm}}>{frame < 120 ? 'Click anywhere…' : `Clicked → frame ${shown} is sharpest there`}</div>
      </div>
      <div style={{position: 'absolute', left: 60, top: 420, width: 330, fontSize: 20, color: C.dim, lineHeight: 1.4, opacity: b}}>
        The click picks the frame with the highest local sharpness around that pixel. No second model run is needed.
      </div>
    </Stage>
  );
};
