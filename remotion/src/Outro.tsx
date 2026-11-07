import React from 'react';
import {C, Photo, Stage} from './common';

export const OUTRO_DUR = 150;

export const Outro: React.FC = () => (
  <Stage title="Credits" dur={OUTRO_DUR}>
    <div style={{position: 'absolute', left: 60, top: 150, display: 'flex', gap: 8}}>
      {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => <Photo key={i} i={i} w={110} />)}
    </div>
    <div style={{position: 'absolute', left: 60, top: 400, width: 1160, fontSize: 28, lineHeight: 1.5}}>
      Based on <b>"Learning to Refocus with Video Diffusion Models"</b><br />
      Tedla, Zhang, Zhang, Xin · ACM SIGGRAPH Asia 2025 · learn2refocus.github.io<br />
      <span style={{color: C.dim, fontSize: 22}}>Built on Stable Video Diffusion (Stability AI) and the EDM training recipe (Karras et al.). Dataset and released weights from the authors. Our re-training, ablations, Blender scenes and viewer: Bhavya.</span>
    </div>
  </Stage>
);
