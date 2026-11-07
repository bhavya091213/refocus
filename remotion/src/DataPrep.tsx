import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {Box, C, Photo, Stage, useIn} from './common';

export const DATA_DUR = 240;

export const DataPrep: React.FC = () => {
  const frame = useCurrentFrame();
  const a = useIn(10), b = useIn(60), c = useIn(110), d = useIn(160);
  const trainW = interpolate(d, [0, 1], [0, 1474 / 1638 * 520]);
  const testW = interpolate(d, [0, 1], [0, 164 / 1638 * 520]);
  return (
    <Stage title="Data and preprocessing" sub="Smartphone focal-stack dataset (Tedla et al.) · only the small 'midsize' archive is used" dur={DATA_DUR}>
      <div style={{position: 'absolute', left: 60, top: 160, opacity: a}}>
        <div style={{display: 'flex', gap: 6}}>{[0, 2, 4, 6, 8].map((i) => <Photo key={i} i={i} w={70} />)}</div>
        <div style={{marginTop: 10, fontSize: 22}}>1. Raw archive</div>
        <div style={{fontSize: 18, color: C.dim, lineHeight: 1.4}}>944 MB zip · 1,643 scene folders<br />14,764 JPEGs · 640×896 px<br />1,638 scenes have all 9 positions</div>
      </div>
      <div style={{position: 'absolute', left: 500, top: 180, opacity: b, transform: `translateY(${(1 - b) * 20}px)`}}>
        <Box x={0} y={0} w={330} h={110} label="2. Resize 640×896" sub="(no-op: already that size)" color={C.accent} />
        <Box x={0} y={130} w={330} h={110} label="3. Scale to [−1, 1]" sub="pixel/127.5 − 1  (VAE input range)" color={C.violet} />
      </div>
      <div style={{position: 'absolute', left: 900, top: 180, opacity: c, width: 320}}>
        <div style={{fontSize: 22}}>4. Encode with frozen VAE</div>
        <div style={{fontSize: 18, color: C.dim, lineHeight: 1.4, marginTop: 6}}>640×896×3 image → 80×112×4 latent<br />(8× smaller per side) · CLIP image embedding of the input photo</div>
      </div>
      <div style={{position: 'absolute', left: 60, top: 470}}>
        <div style={{fontSize: 22, marginBottom: 10}}>5. Fixed train / test split (no overlap)</div>
        <div style={{display: 'flex', gap: 4}}>
          <div style={{width: trainW, height: 46, background: C.accent, borderRadius: 6, color: '#000', fontWeight: 700, lineHeight: '46px', textAlign: 'center', overflow: 'hidden', whiteSpace: 'nowrap'}}>train 1,474</div>
          <div style={{width: testW, height: 46, background: C.warm, borderRadius: 6}} />
        </div>
        <div style={{fontSize: 18, color: C.warm, marginTop: 8}}>test 164 scenes → our evaluation uses every 8th, 20 scenes × input positions 1, 4, 7</div>
        <div style={{fontSize: 18, color: C.dim, marginTop: 4, opacity: d}}>No cropping, no colour change, no augmentation · 5 incomplete folders are in no split</div>
      </div>
    </Stage>
  );
};
