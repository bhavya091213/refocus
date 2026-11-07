import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {Box, C, Photo, Stage, useIn} from './common';

export const COND_DUR = 300;

const Slots: React.FC<{k: number; mode: 'A' | 'B' | 'C'; x: number; y: number; show: number}> = ({k, mode, x, y, show}) => (
  <div style={{position: 'absolute', left: x, top: y, display: 'flex', gap: 5, opacity: show}}>
    {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => {
      const filled = mode === 'A' ? i === k : true;
      return <div key={i} style={{width: 40, height: 56, borderRadius: 5, border: `2px solid ${filled ? C.accent : C.dim}`, background: filled ? '#1d3b52' : '#10151f', color: C.dim, fontSize: 14, textAlign: 'center', lineHeight: '56px'}}>{filled ? (mode === 'A' && i === k ? 'in' : 'in') : '0'}</div>;
    })}
  </div>
);

export const Conditioning: React.FC = () => {
  const frame = useCurrentFrame();
  const arm = frame < 120 ? 'A' : frame < 210 ? 'B' : 'C';
  const k = 4;
  const s1 = useIn(10), s2 = useIn(50);
  const blurIn = interpolate(frame, [0, 60], [0, 1], {extrapolateRight: 'clamp'});
  const desc: Record<string, [string, string]> = {
    A: ['A · random (authors\' scheme)', 'Input latent sits in slot k; the 8 other slots are zeros. The slot index tells the network the input\'s focus position.'],
    B: ['B · ablate_position', 'Input latent copied into all 9 slots: no position signal. The network must guess how blurred the input is.'],
    C: ['C · ablate_time', 'Copied into all slots, but position k is passed through the motion_bucket_id scalar instead.'],
  };
  return (
    <Stage title="How the model sees the input photo" sub="Fine-tuning only the temporal transformer layers of Stable Video Diffusion; VAE and CLIP stay frozen" dur={COND_DUR}>
      <div style={{position: 'absolute', left: 60, top: 150, opacity: s1}}>
        <Photo i={k} w={150} />
        <div style={{fontSize: 18, color: C.dim, marginTop: 6}}>input photo at position {k}</div>
      </div>
      <Box x={260} y={180} w={170} h={70} label="VAE encoder" sub="frozen" opacity={s1} />
      <Box x={260} y={290} w={170} h={70} label="CLIP encoder" sub="frozen" color={C.violet} opacity={s1} fs={20} />
      <div style={{position: 'absolute', left: 480, top: 150, fontSize: 20, color: C.dim, opacity: s2}}>Input latent in 9 slots (4 ch each)</div>
      <Slots k={k} mode={arm as 'A' | 'B' | 'C'} x={480} y={185} show={s2} />
      <div style={{position: 'absolute', left: 480, top: 270, fontSize: 20, color: C.dim, opacity: s2}}>Noisy latent (4 ch × 9 slots)</div>
      <div style={{position: 'absolute', left: 480, top: 305, display: 'flex', gap: 5, opacity: s2}}>
        {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => <div key={i} style={{width: 40, height: 56, borderRadius: 5, background: `repeating-linear-gradient(45deg,#3a3f52 0 4px,#2a2f40 4px 8px)`, border: `2px solid ${C.warm}`}} />)}
      </div>
      <Box x={900} y={210} w={300} h={120} label="Concatenate → 8 channels" sub="+ CLIP embedding (cross-attention)" color={C.good} opacity={s2} />
      <Box x={900} y={380} w={300} h={90} label="SVD U-Net (temporal layers trained)" color={C.accent} opacity={blurIn} fs={20} />
      <div key={arm} style={{position: 'absolute', left: 60, top: 450, width: 800}}>
        <div style={{fontSize: 34, fontWeight: 700, color: C.warm}}>{desc[arm][0]}</div>
        <div style={{fontSize: 24, color: C.ink, marginTop: 8, lineHeight: 1.35}}>{desc[arm][1]}</div>
      </div>
      <div style={{position: 'absolute', left: 900, top: 500, fontSize: 18, color: C.dim, lineHeight: 1.45, width: 330}}>
        Loss: EDM denoising loss on the 9-frame latent. 4,000 steps, lr 2e-5, bf16, 3 arms trained in parallel.
      </div>
    </Stage>
  );
};
